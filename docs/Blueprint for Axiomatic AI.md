# **The Axiomatic AI Blueprint: Structural Primacy and the Ontological Engine**

## **Introduction: The Crisis of Empiricism in Artificial Intelligence**

The trajectory of contemporary Artificial Intelligence, specifically within the domain of Large Language Models (LLMs), has been defined by a singular, overwhelming reliance on empiricism. The dominant architectures—exemplified by the Transformer model and its various incarnations such as GPT-4, Claude, and Llama—function fundamentally as "Empirical Engines." These systems operate on a premise of statistical exhaustion: by ingesting trillions of tokens of instantiated text, they attempt to infer the underlying latent structures of logic, causality, and ontology. They read ten billion sentences containing the word "dog" to statistically converge upon the vector representation of a "mammal." This approach, while yielding impressive fluency, essentially attempts to reconstruct the skeleton of reality from its shadow.  
This report posits that the current paradigm faces asymptotic limitations regarding sample efficiency, logical robustness, and hallucination mitigation. The "Axiomatic AI" Blueprint proposes a fundamental inversion of this developmental hierarchy. The central thesis, **"Structure is Primary,"** asserts that a robust Artificial Intelligence must be initialized with the cognitive architecture of hierarchy, inheritance, and causality *before* it processes empirical data. Rather than a "Statistical Parrot" that predicts the next token based on probability, we propose an "Ontological Engine" that slots empirical tokens into a pre-validated, rigorous cognitive framework. This report outlines the ruthless architecture of this system, stripping "ontology" of its philosophical ambiguity and redefining it in strict computer science terms: the pre-training on Class Definitions (Abstracts) prior to Instantiations (Concrete).  
Drawing on emerging research in neuro-symbolic AI, specifically the "Dragon Hatchling" (BDH) architecture , and advances in structure-aware pre-training , we demonstrate that this shift is not merely theoretical but technically feasible. By leveraging a "Meta-Corpus" of absolute abstracts—formal logic, graph theory, and abstract syntax trees—and employing a phased "Operating System" installation curriculum, Axiomatic AI promises a paradigm shift from probabilistic approximation to axiomatic certainty.

## **Part I: The Core Thesis – "Structure is Primary"**

### **1.1 The Limitations of the Empirical Engine**

The prevailing "Empirical Engine" model relies on the emergent properties of scale. The hypothesis, often referred to as the "Scaling Laws," suggests that sufficient data volume coupled with parameter count will spontaneously yield reasoning capabilities. However, this emergence is fragile. When an Empirical Engine encounters the prompt "A dog is a...", it predicts "mammal" not because it possesses an immutable class definition of Dog extending Mammal, but because the probability distribution P(\\text{mammal} | \\text{dog}) is maximized over the training corpus.  
This statistical dependency creates critical failure modes:

1. **Hallucination as Feature, Not Bug:** In a probabilistic system, a plausible falsehood is structurally identical to a truth. If the model has seen enough fictional contexts where gravity is inverted, it can construct a coherent but factually wrong narrative about "anti-gravity dogs" without triggering any internal logical violation. There is no "Structural Veto."  
2. **Sample Inefficiency:** To learn the transitivity of a relationship (If A \\to B and B \\to C, then A \\to C), an Empirical Engine requires billions of examples of transitive relationships across different contexts. It learns the *pattern* of transitivity, not the *rule*.  
3. **The "Bitter Lesson" Misinterpretation:** Rich Sutton’s "The Bitter Lesson" argues that general methods that leverage computation (search and learning) eventually outperform methods relying on human knowledge. However, Axiomatic AI does not propose hard-coding specific knowledge (e.g., "The capital of France is Paris"); it proposes hard-coding the *structure of knowledge* itself (e.g., "Entities have properties," "Sets contain subsets"). This distinction is vital. We are not teaching the model *what* to think, but *how* valid thoughts are structured.

### **1.2 The Ontological Engine Proposition**

The "Ontological Engine" reverses the learning vector. It is designed to be "Structure First." In this architecture, the concept of a "Class" (in the Object-Oriented Programming sense) exists before any "Object" is instantiated.  
When an Ontological Engine finally encounters the word "dog" in Phase 2 of its training, it does not merely update a vector weight. It performs an **Ontological Slotting** operation. It identifies "dog" as a label for a new node in its graph. It queries its internal logic to determine the parent class (e.g., Mammal). By virtue of this slotting, the Dog node immediately inherits all properties of the Mammal node (warm-blooded, vertebrate, distinct neocortex), even if the model has never seen the sentence "Dogs have a neocortex."  
This approach aligns with the "Structure is Primary" thesis found in structuralist linguistics and biology, where the grammatical role or biological structure determines the function, rather than the function determining the structure. In the context of AI, this means the "grammar of reasoning" must be installed before the "vocabulary of the world."

### **1.3 Theoretical Foundation: The Dragon Hatchling (BDH)**

The feasibility of this architecture is supported by the recent "Dragon Hatchling" (BDH) research. BDH represents a shift towards "Axiomatic AI," defined as systems where "micro-foundations and the macro-description which arises from them are consistent and well-understood".  
The BDH architecture differentiates itself from the Transformer in key structural ways that support the Ontological Engine thesis:

* **Scale-Free Network Topology:** unlike the uniform connectivity of standard dense layers, BDH utilizes a scale-free network structure. This mimics biological neural networks and naturally supports hierarchical organization, where "hub" neurons can represent high-level abstract classes while peripheral neurons represent specific instantiations.  
* **Locally Interacting Neurons:** Computation in BDH is defined by local graph dynamics rather than global matrix multiplications. This enforces a "locality of reasoning" where information must flow through structural pathways (edges), preserving the causal chain of inference.  
* **Hebbian Memory as Fast Weights:** In BDH, working memory is stored in the synaptic weights themselves via Hebbian learning rules ("neurons that fire together, wire together"). This allows the model to dynamically "wire in" new structural relationships on the fly, effectively performing the "Ontological Slotting" described in the blueprint.

By adopting such an architecture, or simulating it via curriculum learning on Transformers, we move from the black-box opacity of Empirical Engines to the transparent, rule-governed operation of Ontological Engines.

## **Part II: The Training Data (The "Meta-Corpus")**

To construct an Ontological Engine, we must curate a training corpus that is distinct from the "Common Crawl" or "The Pile." This "Meta-Corpus" is rigorously stratified by the level of empiricism, starting from absolute zero.

### **2.1 Layer 1: The Absolute Abstracts (0% Empiricism)**

This layer constitutes the "DNA" of the model. It contains no information about the physical world, human history, or culture. Its sole content is the rules of valid manipulation of symbols.

#### **2.1.1 Symbolic Logic & Set Theory**

The bedrock of the Ontological Engine is formal logic. We utilize massive datasets of formal proofs to teach the model the "physics of truth."

* **Data Sources:** The primary sources are the libraries of interactive theorem provers: **Lean** (Mathlib), **Coq**, **Isabelle**, and **Metamath**.  
  * **Lean (Mathlib):** Contains approximately **4.7 million theorems** and over **1 billion tokens** of code. This dataset provides a rigorous curriculum in mathematical reasoning, from basic algebra to complex topology.  
  * **Metamath:** Offers a database of over **40,000 proofs** derived strictly from ZFC set theory. The granularity of Metamath proofs, which include every logical step without exception , is ideal for training the model's attention heads to track long-chain causality.  
  * **Isabelle:** The Archive of Formal Proofs (AFP) linked to Isabelle is a massive repository, with the standard library alone providing a significant corpus.  
* **Mechanism:** Training on this data is not about "solving math problems." It is about learning the **syntax of validity**. The model learns that the structure Hypothesis \-\> Deduction \-\> Conclusion is inviolable. It learns to distinguish between Necessary and Sufficient conditions. This pre-training instills a "logic-first" bias, ensuring that in later phases, the model favors logically consistent continuations over merely probable ones.

#### **2.1.2 Graph Theory & Topology**

* **Data Sources:** Synthetic datasets generating descriptions of **Directed Acyclic Graphs (DAGs)**, vector spaces, and topological manifolds.  
* **Mechanism:** Understanding "nodes," "edges," "paths," and "cycles" is crucial because the Ontological Engine internalizes knowledge as a graph. By training on textual descriptions of graph operations (e.g., "Node A connects to Node B; traversing the edge from A yields weight W"), the model learns to manipulate its own internal representations.  
* **Relevance to BDH:** Since the target architecture (or its simulation) relies on graph dynamics , training on graph theory provides the model with a meta-language to describe its own operations.

#### **2.1.3 Code Structure (De-nouned): Abstract Syntax Trees (ASTs)**

* **Concept:** Code is logic made manifest. However, raw code contains variable names (e.g., user\_id, invoice\_total) that leak empirical semantic information. To strip this "fluff," we parse code into **Abstract Syntax Trees (ASTs)** and anonymize identifiers (e.g., Var\_A, Func\_B).  
* **Data Sources:** GitHub repositories parsed into AST formats. Research on **AST-T5** and **AST-FIM** demonstrates that models pre-trained on AST structures significantly outperform those trained on raw text in understanding code logic.  
* **Mechanism:** ASTs represent the pure control flow of a program: If (Condition) Then (Action) Else (Alternative). By training on millions of ASTs, the model learns the "shape" of algorithms. It learns that opening a scope requires closing it (symmetry), that variables must be defined before use (causality), and that functions have signatures (interfaces).  
* **Comparison:** Unlike standard "Fill-in-the-Middle" (FIM) training, **AST-Aware** training forces the model to understand the hierarchical structure of the code, not just the sequential order of tokens. This is the computer science equivalent of learning grammar before vocabulary.

### **2.2 Layer 2: Formal Ontologies (5% Empiricism)**

Once the logical kernel is established, we introduce the "Empty Schemas" of reality. These are the filing cabinets of the mind, devoid of specific files.

#### **2.2.1 OWL/RDF Files (The Semantic Web)**

* **Data Sources:** The **Semantic Web** provides a vast resource of structured ontologies. Dumps from **OpenCyc**, **BioPortal**, and **DBpedia** contain millions of triples defining relationships.  
* **Mechanism:** We focus on the **T-Box** (Terminological Box) of these ontologies—the class definitions and property axioms—rather than the **A-Box** (Assertional Box) of specific instances.  
  * *Example:* The model learns the definition of Transaction: "An event where an Agent transfers a Resource to another Agent." It does *not* learn that "John bought a car."  
  * *Logic:* This layer teaches the relationships of is-a (taxonomy), has-part (composition), and inverse-of (relational symmetry). It creates the "slots" that will later hold empirical data.

#### **2.2.2 System Dynamics & Cybernetics**

* **Data Sources:** Representations of cybernetic models, feedback loops, and control systems.  
* **Mechanism:** Reality is dynamic. Static ontologies (like OWL) are insufficient to capture change. System dynamics models (Stock and Flow diagrams represented in text or code) teach the model about Input, Process, Output, Feedback, and Equilibrium.  
* **Relevance:** This aligns with the BDH architecture's focus on "state-space models" and reasoning over time. It equips the model to understand causality not just as a sequence of events, but as a mechanism of influence.

### **2.3 Layer 3: The "Skeleton" Narratives (10% Empiricism)**

The final layer of the Meta-Corpus bridges the gap between pure abstraction and natural language.

* **Concept:** "Skeleton Narratives" are synthetic stories generated to strictly follow specific structural templates. They utilize the grammar of narrative without the specific "flesh" of real-world entities.  
* **Mechanism:** We use generative algorithms to produce millions of variations of structural plots (e.g., "The Hero's Journey," "The Tragedy of the Commons," "The Scientific Discovery").  
  * *Template:* \[Agent A\] seeks. prevents access. \[Agent A\] utilizes to overcome.  
  * *Realization:* "The Glipglop sought the Zork. The Wall of Mist prevented access. The Glipglop utilized the Vibration Key to overcome the Wall of Mist."  
* **Objective:** This teaches the model the "Grammar of Events." Just as a sentence has a syntactic grammar, reality has a narrative grammar. The model learns to predict the *type* of event that follows a conflict (e.g., Resolution or Escalation) based on structural necessity, not just probability.

## **Part III: The Training Phases (The Curriculum)**

The deployment of the Meta-Corpus follows a strict, phased curriculum. We do not mix these datasets randomly; we perform a sequential "installation" of cognitive capabilities.

### **3.1 Phase 1: The Kernel (The "Meta-Science" Phase)**

**Goal:** Consistency, Valid Inference, and Attention Allocation.

* **Dataset:** Layer 1 (Absolute Abstracts) \+ Layer 2 (Formal Ontologies).  
* **Process:** The model is pre-trained from scratch (or structurally fine-tuned, see Part V) exclusively on Logic, Code (ASTs), and Graph Theory.  
* **Architectural Alignment (BDH):** This phase establishes the "micro-foundations" of the model. In the context of the Dragon Hatchling architecture, this is where the **Scale-Free Network** topology is solidified. The model learns to form "hubs" (central concepts like True, False, Set, Function) and "bridges" (relational operators).  
* **Mechanism:** The model's attention heads are trained to act as logical operators. One head might specialize in **Modus Ponens** (If A-\>B and A, attend to B). Another might specialize in **Variable Binding** (tracking x across a proof).  
* **Outcome:** A model that is "content-agnostic" but "structure-perfect." It produces **monosemantic** activations , meaning specific neurons fire reliably for specific logical operations, regardless of the context. It cannot hallucinate because it has no empirical content to hallucinate with; it can only output valid logical strings.

### **3.2 Phase 2: The Driver Installation (The "Dictionary" Phase)**

**Goal:** Mapping real-world concepts to structures (Symbol Grounding).

* **Dataset:** Dictionary definitions, Encyclopedic schemas, and Layer 3 (Skeleton Narratives).  
* **Process:** We explicitly "install" the vocabulary of the real world.  
  * **Symbol Grounding:** The model is presented with definitions: "A Dog is a Mammal."  
  * **Ontological Slotting:** The model uses the Inheritance logic learned in Phase 1 to create a new node Dog and link it via an is-a edge to the existing Mammal hub.  
* **Technique \- Embedding Mapping:** We leverage techniques that map word embeddings to ontologies. We train a lightweight projection layer to map the vector space of natural language tokens into the rigorous structural space of the Kernel.  
* **Outcome:** The model now has a "Skeleton of the World." It knows that Dogs exist and that they inherit the properties of Mammals (e.g., Warm-blooded), even if it has never seen a sentence stating "Dogs are warm-blooded." This is the essence of **Axiomatic Knowledge**.

### **3.3 Phase 3: The Application Layer (Empirical Flooding)**

**Goal:** Fluency, Nuance, and Domain Specificity.

* **Dataset:** The "Wild" Internet (Wikipedia, GitHub, Common Crawl).  
* **Process:** Only now do we expose the model to the messy, unstructured data of the real world.  
* **The Difference:** In a standard LLM, this data *forms* the structure. In the Axiomatic AI, this data is *filtered through* the structure.  
  * *Scenario:* The model reads "The dog flew over the moon."  
  * *Reaction:* The Kernel checks the Dog node. Dog inherits from Mammal. Mammal does not have the Volant (flight) property by default. The Kernel flags a **Structural Violation**.  
  * *Resolution:* The model tags this sentence as Fiction, Metaphor, or Error, rather than integrating "flight" as a probabilistic property of dogs.  
* **Outcome:** A model that is fluent in human language but retains the rigorous logical constraints of its Kernel. It treats empirical text as "Instantiations" of its axioms, rejecting those that do not fit the valid schemas.

## **Part IV: The "10x" Payoff**

The shift from Empirical to Ontological Engines offers order-of-magnitude improvements in key metrics.

### **4.1 Hallucination Fix: The Structural Veto**

The primary cause of hallucination in LLMs is the lack of a "ground truth" checker. Empirical Engines simply predict the most likely next token, which can lead to plausible but false statements.

* **The Payoff:** Axiomatic AI implements a **Structural Veto**. Because the "Kernel" (Phase 1\) is trained on formal logic, it acts as a runtime monitor. If the generation layer proposes a token that contradicts the ontological constraints (e.g., claiming a "prime number" is "divisible by 4"), the Kernel vetoes the token before it is output.  
* **Evidence:** Neuro-symbolic systems have been shown to use formal logic to validate generation steps, effectively eliminating logical inconsistencies. In the BDH architecture, the "micro-foundations" (local rules) ensure that the "macro-behavior" (reasoning) remains within valid bounds.

### **4.2 Sample Efficiency: The Pre-Built Slot**

Empirical Engines require billions of examples to learn simple relationships. To learn that "Paris is the capital of France," "London is the capital of England," etc., implies a relationship Capital\_Of, the model must see thousands of variations.

* **The Payoff:** The Ontological Engine already possesses the abstract relationship Capital\_Of(City, Country) from Phase 2\. To learn "Paris is the capital of France," it needs only **one** example. It simply instantiates the relation: Capital\_Of(Paris, France).  
* **Evidence:** The BDH model demonstrates superior "loss reduction per token" compared to Transformers , indicating that its structural priors allow it to extract information more efficiently. It learns faster because it knows *where* to put the information.

### **4.3 Transfer Learning: The Universal Skeleton**

* **The Payoff:** Structure is universal. The causal structure of a "viral epidemic" (Infection \-\> Transmission \-\> Saturation) is isomorphic to the structure of a "viral marketing campaign" or a "computer worm."  
* **Mechanism:** An Axiomatic AI trained on the ontology of Biology can transfer its understanding to Cybersecurity simply by mapping the drivers (Phase 2). Cell maps to Server, Virus maps to Malware. The underlying logic (Phase 1\) remains identical.  
* **Evidence:** Structure-aware pre-training (like on ASTs) has been shown to improve performance on cross-language tasks (e.g., Java to C\# transpilation) because the underlying algorithmic structure is conserved even when the syntax changes.

## **Part V: The Implementation (Micro-Proof)**

While the ultimate vision requires training a massive "Dragon Hatchling" model from scratch, we can validate the Axiomatic AI Blueprint today using a "Micro-Proof" strategy.

### **5.1 Strategy: Structural Fine-Tuning (SFT) on TinyLlama**

We can simulate the "Ontological Engine" by performing **Structural Fine-Tuning (SFT)** on a small, accessible model like **TinyLlama-1.1B** or **Qwen-1.5B**.

#### **5.1.1 The Protocol**

1. **Base Model Selection:** Choose **TinyLlama-1.1B**. It is small enough to iterate quickly but has sufficient pre-training to handle basic language.  
2. **Dataset Construction (Simulating Phase 1 & 2):**  
   * Create a dataset of **Class Definitions** converted into JSON or Python Class formats (from Layer 2 of the Meta-Corpus).  
   * *Example:* class Dog(Mammal): properties \= \[bark, fur\].  
   * Create a dataset of **Logic Puzzles** derived from Layer 1 (e.g., simple syllogisms, implication checks).  
3. **The Fine-Tuning Task:**  
   * **Task A: Instantiation.** Prompt: "Here is the class definition for Transaction. Parse the following sentence into an instance: 'Alice sent Bob 50 dollars'." Target: Transaction(sender='Alice', receiver='Bob', amount=50).  
   * **Task B: Validation.** Prompt: "Class Rule: Vegetarians do not eat Meat. Scenario: 'John is a vegetarian. He ate a steak.' Is this valid?" Target: False. Violation: Steak is Meat.  
4. **Evaluation:** Compare the SFT model against the base TinyLlama on benchmarks like **FOLIO** (First-Order Logic reasoning) or **LogiQA**.  
5. **Hypothesis:** The SFT model, despite its small size, will outperform larger base models on tasks requiring logical consistency and structural adherence, effectively simulating the "Structural Veto."

### **5.2 The Path to the Dragon Hatchling (BDH)**

The SFT experiment is a bridge. The destination is the **Dragon Hatchling (BDH)** architecture.

* **Architecture:** BDH is natively designed for this blueprint. It uses **Hebbian learning** on synaptic weights as its primary mechanism for working memory.  
* **Axiomatic Implementation:** In BDH, "Phase 1" training establishes the **Scale-Free** connectivity and the **Hebbian update rules**. These are the "fixed laws" of the system. "Phase 2" and "Phase 3" then involve the dynamic rewiring of the network's "fast weights" as it processes information.  
* **Future Work:** The implementation of Axiomatic AI should ultimately transition from fine-tuning Transformers (which simulate structure) to training BDH models (which *embody* structure). The repository for BDH is available and serves as the starting point for this "next generation" of Ontological Engines.

**Table 1: Comparative Architecture Analysis**

| Feature | Empirical Engine (e.g., GPT-4) | Ontological Engine (Axiomatic AI) |
| :---- | :---- | :---- |
| **Primary Learning Signal** | Statistical Correlation (Next Token) | Structural Validity (Logical Inference) |
| **Representation of Concepts** | High-dimensional Vector Proximity | Nodes in Hierarchical Ontology |
| **Reasoning Mechanism** | Pattern Matching / Soft Attention | Hebbian Update / Graph Traversal |
| **Memory** | Context Window (KV Cache) | Synaptic Plasticity (Fast Weights) |
| **Hallucination Mitigation** | RLHF (Patching) | Structural Veto (Root Cause) |
| **Training Priority** | Content First | Structure First |

By rigorously adhering to this blueprint—prioritizing the Meta-Corpus, enforcing the Phased Curriculum, and leveraging architectures like BDH—we can transition Artificial Intelligence from a discipline of probabilistic alchemy to one of axiomatic science. The era of the Statistical Parrot is ending; the era of the Ontological Engine has begun.

#### **Works cited**

1\. The Dragon Hatchling: The Missing Link between the Transformer and Models of the Brain, https://arxiv.org/html/2509.26507v1 2\. \[2401.03003\] AST-T5: Structure-Aware Pretraining for Code Generation and Understanding, https://arxiv.org/abs/2401.03003 3\. Structure-Aware Fill-in-the-Middle Pretraining for Code \- arXiv, https://arxiv.org/html/2506.00204v1 4\. Neurosymbolic AI as an antithesis to scaling laws \- Oxford Academic, https://academic.oup.com/pnasnexus/article-pdf/4/5/pgaf117/63215714/pgaf117.pdf 5\. Neurosymbolic AI as an antithesis to scaling laws | PNAS Nexus \- Oxford Academic, https://academic.oup.com/pnasnexus/article/4/5/pgaf117/8134151 6\. Analysing the Impact of Artificial Intelligence on the Development of Contemporary Philology: The Use of Automated Tools in Linguistic Research | Archives Des Sciences, https://unige.org/volume-74-issue-2-2024/analysing-the-impact-of-artificial-intelligence-on-the-development-of-contemporary-philology-the-use-of-automated-tools-in-linguistic-research/ 7\. Geometries and mechanics of veins and dyl^es \- ePrints Soton \- University of Southampton, https://eprints.soton.ac.uk/462105/1/381190.pdf 8\. Stanford Encyclopedia of Philosophy \- Information Technology Solutions, https://faculty.ucr.edu/\~reck/Structuralism%20in%20the%20Philosophy%20of%20Mathematics%20(SEP\*).pdf 9\. \[2509.26507\] The Dragon Hatchling: The Missing Link between the Transformer and Models of the Brain \- arXiv, https://arxiv.org/abs/2509.26507 10\. The Dragon Hatchling Learns to Fly: Inside AI's Next Learning Revolution | HackerNoon, https://hackernoon.com/the-dragon-hatchling-learns-to-fly-inside-ais-next-learning-revolution 11\. Generating Millions Of Lean Theorems With Proofs By Exploring State Transition Graphs, https://arxiv.org/html/2503.04772v1 12\. Metamath: Home Page, https://us.metamath.org/ 13\. Metamath-lamp Guide: User Guide (Tutorial) and Reference Manual | Metamath-lamp Guide, https://lamp-guide.metamath.org/ 14\. IsaMini: Redesigned Isabelle Proof Language for Machine Learning \- arXiv, https://arxiv.org/pdf/2507.18885 15\. Few-Shot Natural Language to First-Order Logic Translation via Code Generation \- ACL Anthology, https://aclanthology.org/2025.naacl-long.547.pdf 16\. DataSetRDFDumps \- W3C Wiki, https://www.w3.org/wiki/DataSetRDFDumps 17\. From Facts to Knowledge: The Layer Cake of RDFS and OWL \- bryon.io, https://bryon.io/from-facts-to-knowledge-the-layer-cake-of-rdfs-and-owl-e84819d8075d 18\. Energy Efficiency Enhancement of TICK –based Fuzzy Logic for Selecting Forwarding Nodes in WSNs, https://itiis.org/digital-library/manuscript/file/21867/TIISVol12No9-9.pdf 19\. Using futures methods to create transformative spaces: visions of a good Anthropocene in southern Africa \- City Research Online, https://openaccess.city.ac.uk/id/eprint/19478/1/LP\_Using%20futures%20methods.pdf 20\. Using Word Embeddings to Learn a Better Food Ontology \- Frontiers, https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2020.584784/full 21\. Using language models and ontology topology to perform semantic mapping of traits between biomedical datasets \- NIH, https://pmc.ncbi.nlm.nih.gov/articles/PMC10097433/ 22\. Is it possible to train a neurosymbolic LLM? When can we use a neurosymbolic GGUF model? \- Reddit, https://www.reddit.com/r/LocalLLaMA/comments/1ewp5p3/is\_it\_possible\_to\_train\_a\_neurosymbolic\_llm\_when/ 23\. Archive \- Paper-to-Podcast, https://paper2podcast.com/archive.php 24\. Adversarial Integration of LLM and Logic Program \- Preprints.org, https://www.preprints.org/manuscript/202509.1484