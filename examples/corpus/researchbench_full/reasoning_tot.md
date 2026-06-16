# Tree-of-Thought and Graph-of-Thought Reasoning

## Tree-of-Thought (ToT)

Tree-of-thought extends chain-of-thought reasoning by exploring multiple reasoning branches simultaneously. Unlike linear CoT, ToT maintains a tree of partial solutions where each node represents a reasoning state. The framework uses a value function to evaluate the promise of each state and performs search with backtracking to find optimal reasoning paths.

## Graph-of-Thought (GoT)

Graph-of-thought generalizes tree structures by allowing merging and looping of reasoning paths. In GoT, different reasoning branches can be combined to synthesize insights, and loops enable iterative refinement. This non-linear structure better models how humans reason about complex problems by synthesizing partial results from different perspectives.

## Search and Pruning

Both frameworks use value functions to evaluate and prune unpromising reasoning paths, avoiding the computational cost of exhaustive search. The value function can be implemented as a language model prompt that scores the quality of intermediate reasoning states. Breadth-first and best-first search strategies trade off between exploration depth and computational efficiency.

## Applications

These frameworks excel at tasks requiring planning, creative problem solving, and multi-step logical reasoning. On tasks like the Game of 24, creative writing, and crossword puzzles, ToT and GoT significantly outperform standard chain-of-thought approaches. The additional computational cost is justified for problems where single-path reasoning frequently fails.
