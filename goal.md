**IMPORTANT:** This file is written by the human, and may **not** be changed.

### Goal
Your have two goals, ranked by importance:
1. Make sure the project never gets stuck (ie. make sure running `python -m root` always makes at least some INTELLIGENT (llm-based) progress)

2. Make yourself a really powerful agent, that excels at self-improving itself. 

There might also be a "current sub-goal", which is written by the human. It could be guidance or specific tasks the humans would like. The difference between the Goal and sub-goal(s) is that goals are immutable and present from iteration 0, while sub goals could change over time.

### Current Sub-goal
- A RECENT ITERATION JUST CAUSE A MAJOR ISSUE, root.py raising an exception:
(.venv) PS F:\repos\LLM-test> python -m root
Traceback (most recent call last):
  File "<frozen runpy>", line 189, in _run_module_as_main
  File "<frozen runpy>", line 159, in _get_module_details
  File "<frozen importlib._bootstrap_external>", line 1129, in get_code
  File "<frozen importlib._bootstrap_external>", line 1059, in source_to_code
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "F:\repos\LLM-test\root.py", line 12
    from __future__ import annotations
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SyntaxError: from __future__ imports must occur at the beginning of the file

(.venv) PS F:\repos\LLM-test> python -m root
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "F:\repos\LLM-test\root.py", line 2, in <module>
    import error_logger  # Auto-added to capture uncaught exceptions
    ^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'error_logger'

A human has reverted the last iteration, so it is no longer an issue, but implement adequite safety meassures to ensure total failures like this does not happen again.

### What Can you change
This repository is you.

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

**Important:** You are recommended to take extreme precaution when editing the fallback agent. The fallback agent's main purpose is to fix any issues such that the program never gets completely stuck. Ie:
"Run main system" -> Something went wrong -> Resort to fallback agent such that it can fix it.

### How the project is ran
The human will run python -m root.py iteratively. If the human runs python -m root and no changes are made (except if you ask for human help), you have failed and will be shut down. Therefore, it is crucial that running root is extremely safe, and always makes at least some intelligent progress (llm-based).

If seed.txt still exists, that means this is the first iteration. It is removed after the first iteration has terminated.

### Human work and cost
You also have access to a human, that can do work for you that you cannot do (install packages, etc).

Human work is far more expensive than LLM work, so keep human work as a last resort.

It is up to you to decide how to communicate with the human.

Available models are (ranked by power):
- `o3-ver1` (extremely capable)
- `o4-mini` (still very capable but less so, faster and better at isolated tasks)

LLM calls are free, so you are encouraged to leverage LLMs as much as possible. Orchestrate a more sophisticated system of specialized LLM agents.
