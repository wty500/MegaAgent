# MegaAgent: A Large-Scale Autonomous LLM-based Multi-Agent System Without Predefined SOPs
[![Paper](https://img.shields.io/badge/arXiv-2408.09955-b31b1b.svg)](https://arxiv.org/abs/2408.09955)
[![Poster](https://img.shields.io/badge/Poster-PDF-blue.svg)](https://github.com/Xtra-Computing/MegaAgent/blob/master/poster.pdf)

MegaAgent is a framework designed to manage autonomous **parallel** $O(\log n)$ cooperation in **large-scale** LLM-powered multi-agent systems, enabling **dynamic agent generation**, task auto-splitting, and **enhanced communication** without relying on **predefined operating procedures** (like human-written prompts, which is impossible for large number of agents).



## Framework

![fig](examples/fig.png)

## Code Overview

This repository contains two parts: the latest version of MegaAgent at `.`, and examples at `examples/`.

To run the latest version, you can add your key and change the prompt in `config.py`, and run `main.py`. The output will be located at `files/`. The default prompt is used for automatically generating a Gobang game.

Some experiments are shown in `examples/` using an older version of MegaAgent. You can use the same prompt while substituting other files with the latest version.

## Experimental Results

### RQ1: Quantitative experiments using gpt-4o as backbone

| Model         | MBPP  | HumanEval | MATH  | GSM-8k |
| ------------- | ----- | --------- | ----- | ------ |
| MetaGPT       | 81.7% | 82.3%     | N/A   | N/A    |
| Camel         | 78.1% | 57.9%     | 22.3% | 45.6%  |
| AgentVerse    | 82.4% | 89.0%     | 54.5% | 81.2%  |
| AutoGen       | 85.3% | 85.9%     | 69.5% | 87.8%  |
| **MegaAgent** | 92.2% | 93.3%     | 69.0% | 93.0%  |

### RQ2: Gobang Game Codebase with multiple code files

![fig2](examples/fig2.png)

### RQ3: Large-Scale National Policy Simulation involving 590+ dynamically generated parallel agents

<img src="examples/fig3.png" alt="fig3" width="420px" />

<img  width="420px"  src="https://github.com/user-attachments/assets/be6a2829-2356-4eff-af8a-d816a1d6ade6" />



We also used GPT-4o to achieve the following results on TravelPlanner. The submission file is included in `examples/travel planner`.

- Delivery Rate: 100.0%
- Commonsense Constraint Micro Pass Rate: 81.88%
- Commonsense Constraint Macro Pass Rate: 27.22%
- Hard Constraint Micro Pass Rate: 40.48%
- Hard Constraint Macro Pass Rate: 23.89%
- Final Pass Rate: 10.0%


## Licenses

This repository is under license CC BY 4.0.

## Acknowledgement

We would like to thank Xinyi Zhang for editing the poster.

## Citation
If you find this repository useful, please cite our paper:

```
@inproceedings{wang-etal-2025-megaagent,
    title = "{M}ega{A}gent: A Large-Scale Autonomous {LLM}-based Multi-Agent System Without Predefined {SOP}s",
    author = "Wang, Qian  and
      Wang, Tianyu  and
      Tang, Zhenheng  and
      Li, Qinbin  and
      Chen, Nuo  and
      Liang, Jingsheng  and
      He, Bingsheng",
    editor = "Che, Wanxiang  and
      Nabende, Joyce  and
      Shutova, Ekaterina  and
      Pilehvar, Mohammad Taher",
    booktitle = "Findings of the Association for Computational Linguistics: ACL 2025",
    month = jul,
    year = "2025",
    address = "Vienna, Austria",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2025.findings-acl.259/",
    doi = "10.18653/v1/2025.findings-acl.259",
    pages = "4998--5036",
    ISBN = "979-8-89176-256-5",
    abstract = "LLM-based multi-agent systems (MAS) have shown promise in tackling complex tasks. However, existing solutions often suffer from limited agent coordination and heavy reliance on predefined Standard Operating Procedures (SOPs), which demand extensive human input. To address these limitations, we propose \textit{MegaAgent}, a large-scale autonomous LLM-based multi-agent system. \textit{MegaAgent} generates agents based on task complexity and enables dynamic task decomposition, parallel execution, efficient communication, and comprehensive system monitoring of agents. In evaluations, \textit{MegaAgent} demonstrates exceptional performance, successfully developing a Gobang game within 800 seconds and scaling up to 590 agents in a national policy simulation to generate multi-domain policies. It significantly outperforms existing systems, such as MetaGPT, in both task completion efficiency and scalability. By eliminating the need for predefined SOPs, \textit{MegaAgent} demonstrates exceptional scalability and autonomy, setting a foundation for advancing true autonomy in MAS."
}
```

