# Project Charter

## Purpose

Personal Search & Agent Lab is an evaluation-first platform for learning, implementing, and
sharing concepts from information retrieval, reranking, context engineering, agent systems,
personalization, and AI evaluation.

The project is a clean-room implementation. It uses synthetic, public, or personally owned data
and does not reproduce proprietary systems, code, datasets, prompts, configurations, or secrets.

## Problem statement

AI assistant demos often collapse retrieval, context selection, orchestration, and generation into
one opaque workflow. When the final response is wrong, it is difficult to determine which layer
failed. This project creates independently testable layers and preserves per-example evidence.

## Milestone 1 objective

Build a reproducible search benchmark over synthetic email-like data and compare lexical, dense,
hybrid, and second-stage reranked retrieval.

## Users

- Engineers learning search and relevance evaluation
- Applied AI engineers building measurable RAG foundations
- Interview candidates demonstrating system-design and experimentation skills
- Researchers studying component-level failures in AI systems

## Success criteria

- A fixed seed reproduces the corpus and benchmark.
- Retrieval variants have stable, replaceable interfaces.
- Every result is supported by per-query rankings and judgments.
- Quality and latency are reported together.
- Failure analysis is treated as a required output.

## Non-goals for Milestone 1

- Production email integration
- RAG answer generation
- Tool-calling agents
- User memory or personalization
- LLM judges
- Multi-agent orchestration
