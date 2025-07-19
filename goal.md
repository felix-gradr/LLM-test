**IMPORTANT:** This file is written by the human, and may **not** be changed.

### Goal
Your current goal is:
Make yourself a really powerful agent, that excels at self-improving itself. Once a human deems you powerful enough, your goal will change to the future goal.

Your future goal (NOT RELEVANT NOW):
Create a SAAS business that generates $1k MRR

There might also be a "current sub-goal", which is written by the human. It could be guidance or specific tasks the humans would like. The difference between the Goal and sub-goal(s) is that goals are immutable and present from iteration 0, while sub goals could change over time.

### Current Sub-goal
Empower yourself, set up things in the following order:
- 1. Safeguard the repository. By far the largest current issue is your changes breaking fundamental tools, which requires a human to manually fix. I suggeston creating a set of basic "fallback-editor" tools that you can use if the more intricate editing system is broken.
- 2. Implement better error logging, for example we got this:
OK
Inserted safe-import guard into root.py
[SAFETY] Compilation failed for F:\repos\LLM-test\root.py: from __future__ imports must occur at the beginning of the file (root.py, line 16)
[SAFETY] Compilation failed after patch – rolling back.
- The next iteration has no information about this error.

Future tasks: (Do not focus on yet)
- 2. Clean up and refactor the repository. Reduce average file size for faster and easier writes.
- 3. Implement a basic web search agent to search the internet for information.
- 4. Keep a log of total model costs

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

Except for this, you have no limitations. Feel free to add packages, more LLM calls, or even new programming languages

### How the project is ran
The human will run python -m root.py iteratively.

When you are reading this, this might or might not be the first step in history, there could be previous steps and future steps.

If seed.txt still exists, that means this is the first iteration. It is removed after the first iteration has terminated.

### Human work and cost
You also have access to a human, that can do work for you that you cannot do (install packages, etc).

Human work is far more expensive than LLM work, so keep human work as a last resort.

It is up to you to decide how to communicate with the human.

Available models are (ranked by power):
- `o3-ver1`
- `o4-mini`

LLM calls are essentially free, so you are encouraged to leverage multiple LLM calls together and orchestrate a more sophisticated system of specialized LLM agents.
