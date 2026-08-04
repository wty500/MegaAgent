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

### Backbone / API interface

The main MegaAgent code (`.`) and the TravelPlanner example talk to the model
through the modern OpenAI Python SDK tool-use interface (`tools` /
`tool_calls` / `role:"tool"`). The shared transport lives in a single file,
`llm_core.py`, which their `llm.py` delegates to; all framework logic, prompts,
and tool schemas are unchanged from the original design. Configure the backbone
in `config.py`:

```python
api_key = 'YOUR_KEY'
model = "gpt-5.6-sol"
base_url = 'https://your-endpoint/v1'
reasoning_effort = 'xhigh'   # optional; sent only when set
```

`llm_core.py` streams every request internally (reassembling one complete
response), sends no `temperature` and never caps `max_tokens` (so long
reasoning is never truncated), and sanitizes histories to the strict tool-use
protocol. Install dependencies with `pip install -r requirements.txt`.

The other examples under `examples/` still use the legacy
`functions`/`function_call` interface with `url` in their `config.py`.

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



We also evaluated MegaAgent on TravelPlanner (validation set, sole-planning
mode). The submission file (`merged_plans.jsonl`) is included in
`examples/travel planner`.

| Metric | GPT-4o | GPT-5.6 |
| ------ | ------ | ------- |
| Delivery Rate | 100.0% | 100.0% |
| Commonsense Constraint Micro Pass Rate | 81.88% | 97.64% |
| Commonsense Constraint Macro Pass Rate | 27.22% | 84.44% |
| Hard Constraint Micro Pass Rate | 40.48% | 87.14% |
| Hard Constraint Macro Pass Rate | 23.89% | 83.33% |
| **Final Pass Rate** | **10.0%** | **76.67%** |

The GPT-5.6 column uses `gpt-5.6-sol` with `reasoning_effort=xhigh` through the
tool-use interface described above.


## Licenses

This repository is under license CC BY 4.0.

## Citation
If you find this repository useful, please cite our paper:

```
@article{wang2024megaagent,
  title={Megaagent: A practical framework for autonomous cooperation in large-scale llm agent systems},
  author={Wang, Qian and Wang, Tianyu and Li, Qinbin and Liang, Jingsheng and He, Bingsheng},
  journal={arXiv e-prints},
  pages={arXiv--2408},
  year={2024}
}
```
