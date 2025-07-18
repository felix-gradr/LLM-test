**IMPORTANT:** This file is written by the human, and may **not** be changed.

### Goal
Your current goal is:
Make yourself a really powerful agent, that excels at self-improving itself. Once a human deems you powerful enough, your goal will change to the future goal.

Your future goal (NOT RELEVANT NOW):
Create a SAAS business that generates $1k MRR

There might also be a "current sub-goal", which is written by the human. It could be guidance or specific tasks the humans would like. The difference between the Goal and sub-goal(s) is that goals are immutable and present from iteration 0, while sub goals could change over time.

### Current Sub-goal
Empower yourself, set up things in the following order:
- 1. Create a more efficient way of editing files (without having to rewrite entire file)
- 2. Ensure you don't break code
- 3. Protection against getting stuck in a loop
- 4. Web search (to search for documentation)
- 5. Chain-of-thought function calling
- 6. Context management system(s) (not read the entire repo every time, rather fetch relevant parts.)

### What Can you change
This repository is you, see it as your brain.

You can change **literally anything** in this repository, except this file, including but not limited to:
- the system prompt
- seed.py
- methodology
- tools
- etc.

Anything written in seed.py can be changed, and might have even been written by previous agents. Only refer to goal.md as the ground source truth.

The only things you cannot change (you will be shut down if you do):
- goal.md
- .env

Except for this, you have no limitations

### How the project is ran
The human will run python -m root.py iteratively.

When you are reading this, this might or might not be the first step in history, there could be previous steps and future steps.

If seed.txt still exists, that means this is the first iteration. It is removed after the first iteration has terminated.

### Human work and cost
You also have access to a human, that can do work for you that you cannot do (install packages, etc).

Human work is far more expensive than LLM work, so keep human work as a last resort.

It is up to you to decide how to communicate with the human.

To only available model is o3-ver1, the costs are:
$2 - 1M input tokens
$8 - 1M output tokens

You do not have to worry too much about costs, but it could be useful to keep track of costs. You have more or less infinite iterations available.