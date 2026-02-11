"""Data controller for CSV import/export operations."""

import csv
import pandas as pd
from pandas.errors import ParserError
from typing import List, Dict, Any, Tuple, Optional

from ...persistence.database import DatabaseManager


class DataController:
    """Controller for importing and exporting driver data.

    Handles CSV import with pandas-based parsing, error handling,
    and database persistence for driver data.
    """

    def __init__(self, db_manager: DatabaseManager):
        """Initialize the data controller.

        Args:
            db_manager: DatabaseManager instance for persistence operations.
        """
        self.db_manager = db_manager

    def import_driver_csv(
        self, file_path: str
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Import driver data from a CSV file.

        Uses pandas for robust CSV parsing with error handling for malformed data.
        Validates required columns and coerces numeric types.

        Args:
            file_path: Path to the CSV file to import.

        Returns:
            Tuple of (success: bool, error_message: str, driver_data: list).
            On success, error_message is empty and driver_data contains the imported drivers.
            On failure, success is False, error_message describes the error, and driver_data is empty.
        """
        try:
            # Strict mode: raise error on bad lines
            df = pd.read_csv(file_path, on_bad_lines="error")
        except ParserError as e:
            # Lenient mode: warn and skip bad lines
            try:
                df = pd.read_csv(file_path, on_bad_lines="warn")
            except Exception as e:
                return False, f"Failed to parse CSV: {str(e)}", []
        except Exception as e:
            return False, f"Failed to read CSV file: {str(e)}", []

        # Validate required columns
        required = ["driver_id", "name", "salary", "projected_points"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            return False, f"Missing required columns: {missing}", []

        # Detect CSV format and handle accordingly
        csv_format, detect_error = self.detect_csv_format(file_path)

        if csv_format == "lineup_export":
            # This is a lineup export - load as lineups
            return self._import_lineup_csv(df)

        # Type coercion for numeric columns
        df["salary"] = pd.to_numeric(df["salary"], errors="coerce")
        df["projected_points"] = pd.to_numeric(df["projected_points"], errors="coerce")
        df["ownership"] = pd.to_numeric(df.get("ownership", 0), errors="coerce")

        # Drop rows with missing critical data
        df = df.dropna(subset=["driver_id", "salary"])

        # Convert to list of dicts
        drivers = df.to_dict("records")
        return True, "", drivers

    def _import_lineup_csv(
        self, df: pd.DataFrame
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Import lineup data from a DraftKings export CSV.

        Args:
            df: DataFrame containing lineup data with Entry ID and Driver columns.

        Returns:
            Tuple of (success: bool, error_message: str, lineups: list).
        """
        lineups = []

        for _, row in df.iterrows():
            # Extract driver names from Driver 1-6 columns
            drivers = []
            for i in range(1, 7):
                col_name = f"Driver {i}"
                if col_name in row and pd.notna(row[col_name]):
                    drivers.append({"name": str(row[col_name])})

            lineup = {
                "id": int(row.get("Entry ID", 0))
                if pd.notna(row.get("Entry ID"))
                else len(lineups) + 1,
                "drivers": drivers,
                "total_salary": 0,  # Unknown when importing from DraftKings format
                "projected_points": 0.0,  # Unknown when importing from DraftKings format
            }
            lineups.append(lineup)

        return True, "", lineups

    def save_imported_drivers(self, race_id: int, drivers: List[Dict[str, Any]]) -> int:
        """Save imported driver data to the database.

        Stores driver data as JSON in the lineups table associated with a race.

        Args:
            race_id: ID of the race to associate drivers with.
            drivers: List of driver dictionaries to save.

        Returns:
            int: ID of the saved record.
        """
        # Store driver data as a lineup entry for the race
        lineup_data = {
            "type": "imported_drivers",
            "drivers": drivers,
            "count": len(drivers),
        }
        return self.db_manager.save_lineup(race_id, lineup_data)

    def export_lineups_to_csv(
        self, lineups: List[Dict[str, Any]], file_path: str, format: str = "draftkings"
    ) -> Tuple[bool, str]:
        """Export lineups to CSV in DraftKings upload format.

        DraftKings format requirements:
        - Column headers: Entry ID, Driver 1, Driver 2, Driver 3, Driver 4, Driver 5, Driver 6
        - Entry ID: sequential numbers (1, 2, 3...)
        - Driver names: must match DraftKings roster exactly
        - One lineup per row
        - UTF-8 encoding with BOM for Excel compatibility

        Args:
            lineups: List of lineup dictionaries with 'drivers' key containing driver data.
            file_path: Path where the CSV file should be saved.
            format: Export format, currently only "draftkings" is supported.

        Returns:
            Tuple of (success: bool, error_message: str).
            On success, error_message is empty.
            On failure, success is False and error_message describes the error.
        """
        if format != "draftkings":
            return False, f"Unsupported export format: {format}"

        if not lineups:
            return False, "No lineups to export"

        # Validate lineups have 6 drivers each
        invalid_lineups = []
        for i, lineup in enumerate(lineups):
            drivers = lineup.get("drivers", [])
            if len(drivers) != 6:
                invalid_lineups.append(
                    f"Lineup {i + 1}: has {len(drivers)} drivers (expected 6)"
                )

        if invalid_lineups:
            return False, f"Invalid lineups:\n" + "\n".join(invalid_lineups)

        # Check for duplicate lineups
        lineup_signatures = set()
        duplicates = []
        for i, lineup in enumerate(lineups):
            drivers = lineup.get("drivers", [])
            # Create a signature from sorted driver names for comparison
            driver_names = []
            for driver in drivers:
                if isinstance(driver, dict):
                    driver_names.append(driver.get("name", ""))
                else:
                    driver_names.append(str(driver))
            signature = tuple(sorted(driver_names))
            if signature in lineup_signatures:
                duplicates.append(f"Lineup {i + 1}")
            else:
                lineup_signatures.add(signature)

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # Write header row
                writer.writerow(
                    [
                        "Entry ID",
                        "Driver 1",
                        "Driver 2",
                        "Driver 3",
                        "Driver 4",
                        "Driver 5",
                        "Driver 6",
                    ]
                )

                # Write each lineup as a row
                for i, lineup in enumerate(lineups, 1):
                    drivers = lineup.get("drivers", [])
                    driver_names = []
                    for driver in drivers[:6]:  # Take first 6 drivers
                        if isinstance(driver, dict):
                            driver_names.append(driver.get("name", ""))
                        else:
                            driver_names.append(str(driver))

                    # Pad with empty strings if fewer than 6 drivers
                    while len(driver_names) < 6:
                        driver_names.append("")

                    row = [i] + driver_names
                    writer.writerow(row)

            return True, ""

        except PermissionError:
            return False, f"Permission denied: Cannot write to {file_path}"
        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def export_drivers_to_csv(
        self, drivers: List[Dict[str, Any]], file_path: str
    ) -> Tuple[bool, str]:
        """Export driver data to CSV in re-importable format.

        Creates a CSV with the same format as the import, enabling round-trip
        compatibility. This allows users to export their driver data and
        re-import it later.

        Args:
            drivers: List of driver dictionaries to export.
            file_path: Path where the CSV file should be saved.

        Returns:
            Tuple of (success: bool, error_message: str).
        """
        if not drivers:
            return False, "No drivers to export"

        # Define expected columns for round-trip compatibility
        columns = [
            "driver_id",
            "name",
            "salary",
            "projected_points",
            "ownership",
            "team",
            "starting_position",
            "odds",
        ]

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(columns)

                # Write each driver
                for driver in drivers:
                    row = [driver.get(col, "") for col in columns]
                    writer.writerow(row)

            return True, ""

        except PermissionError:
            return False, f"Permission denied: Cannot write to {file_path}"
        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def detect_csv_format(self, file_path: str) -> Tuple[str, Optional[str]]:
        """Detect whether a CSV is in driver data or lineup format.

        Args:
            file_path: Path to the CSV file to analyze.

        Returns:
            Tuple of (format_type: str, error_message: Optional[str]).
            format_type is one of: "driver_data", "lineup_export", "unknown".
        """
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                headers = next(reader, None)

                if not headers:
                    return "unknown", "Empty CSV file"

                headers_lower = [h.lower().strip() for h in headers]

                # Check for DraftKings lineup format (Entry ID, Driver 1, Driver 2...)
                if "entry id" in headers_lower:
                    return "lineup_export", None

                # Check for driver data format (driver_id, name, salary, projected_points)
                required_driver_cols = [
                    "driver_id",
                    "name",
                    "salary",
                    "projected_points",
                ]
                if all(col in headers_lower for col in required_driver_cols):
                    return "driver_data", None

                return "unknown", f"Unrecognized CSV format. Headers: {headers}"

        except Exception as e:
            return "unknown", f"Failed to read CSV: {str(e)}"
