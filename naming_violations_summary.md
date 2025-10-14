# Naming Violations Report

**Generated:** Tue Oct 14 05:06:16 AM CEST 2025

## Summary

- **Total Violations:** 1440
- **Critical:** 0
- **High:** 79
- **Medium:** 769
- **Low:** 592

## Violations by Type

- **Directory Plural:** 71
- **Directory Ambiguous:** 1
- **Directory Deep Nesting:** 5
- **Variable Single Letter:** 592
- **Function No Verb Noun:** 687
- **Variable Hungarian Notation:** 74
- **Function Boolean Flag:** 6
- **File Not Snake Case:** 3
- **File Cryptic Name:** 1

## High Priority Violations

### projects
- **File:** `projects`
- **Issue:** Directory 'projects' uses plural form, should be singular
- **Suggested:** `project`
- **Rule:** Prefer Singular Names for Directories

### hf_spaces
- **File:** `hf_spaces`
- **Issue:** Directory 'hf_spaces' uses plural form, should be singular
- **Suggested:** `hf_space`
- **Rule:** Prefer Singular Names for Directories

### k8s
- **File:** `k8s`
- **Issue:** Directory 'k8s' uses plural form, should be singular
- **Suggested:** `k8`
- **Rule:** Prefer Singular Names for Directories

### .hypothesis
- **File:** `.hypothesis`
- **Issue:** Directory '.hypothesis' uses plural form, should be singular
- **Suggested:** `.hypothesi`
- **Rule:** Prefer Singular Names for Directories

### tmp
- **File:** `tmp`
- **Issue:** Directory name 'tmp' is ambiguous and unclear
- **Suggested:** `Use descriptive name based on contents`
- **Rule:** Be Descriptive and Specific

### entities
- **File:** `tests/entities`
- **Issue:** Directory 'entities' uses plural form, should be singular
- **Suggested:** `entitie`
- **Rule:** Prefer Singular Names for Directories

### js
- **File:** `tests/js`
- **Issue:** Directory 'js' uses plural form, should be singular
- **Suggested:** `j`
- **Rule:** Prefer Singular Names for Directories

### adapters
- **File:** `tests/adapters`
- **Issue:** Directory 'adapters' uses plural form, should be singular
- **Suggested:** `adapter`
- **Rule:** Prefer Singular Names for Directories

### properties
- **File:** `tests/properties`
- **Issue:** Directory 'properties' uses plural form, should be singular
- **Suggested:** `propertie`
- **Rule:** Prefer Singular Names for Directories

### next-priorities-analysis
- **File:** `projects/next-priorities-analysis`
- **Issue:** Directory 'next-priorities-analysis' uses plural form, should be singular
- **Suggested:** `next-priorities-analysi`
- **Rule:** Prefer Singular Names for Directories

*... and 69 more high violations*

## Medium Priority Violations

### .remote_sync/opt_docserver/src/adapters/database
- **File:** `.remote_sync/opt_docserver/src/adapters/database`
- **Issue:** Directory nesting depth 5 exceeds recommended 4 levels
- **Suggested:** `Consider flattening directory structure`
- **Rule:** Avoid Deep Nesting and Ambiguity

### .remote_sync/opt_docserver/src/adapters/web
- **File:** `.remote_sync/opt_docserver/src/adapters/web`
- **Issue:** Directory nesting depth 5 exceeds recommended 4 levels
- **Suggested:** `Consider flattening directory structure`
- **Rule:** Avoid Deep Nesting and Ambiguity

### training/models/qwen3-8b-q5-k-m/.cache/huggingface
- **File:** `training/models/qwen3-8b-q5-k-m/.cache/huggingface`
- **Issue:** Directory nesting depth 5 exceeds recommended 4 levels
- **Suggested:** `Consider flattening directory structure`
- **Rule:** Avoid Deep Nesting and Ambiguity

### training/models/qwen3-8b-q5-k-m/.cache/huggingface/download
- **File:** `training/models/qwen3-8b-q5-k-m/.cache/huggingface/download`
- **Issue:** Directory nesting depth 6 exceeds recommended 4 levels
- **Suggested:** `Consider flattening directory structure`
- **Rule:** Avoid Deep Nesting and Ambiguity

### training/models/.cache/huggingface/download
- **File:** `training/models/.cache/huggingface/download`
- **Issue:** Directory nesting depth 5 exceeds recommended 4 levels
- **Suggested:** `Consider flattening directory structure`
- **Rule:** Avoid Deep Nesting and Ambiguity

### analyze_function_length
- **File:** `analyze_functions.py`
- **Line:** 10
- **Issue:** Function 'analyze_function_length' should follow verb-noun pattern
- **Suggested:** `process_analyze_function_length`
- **Rule:** Form Verb-Noun Pairs

### main
- **File:** `analyze_functions.py`
- **Line:** 43
- **Issue:** Function 'main' should follow verb-noun pattern
- **Suggested:** `process_main`
- **Rule:** Form Verb-Noun Pairs

### integrator
- **File:** `test_pr_integration.py`
- **Line:** 91
- **Issue:** Variable 'integrator' uses Hungarian notation, should be 'egrator'
- **Suggested:** `egrator`
- **Rule:** Avoid Encodings

### main
- **File:** `naming_audit.py`
- **Line:** 388
- **Issue:** Function 'main' should follow verb-noun pattern
- **Suggested:** `process_main`
- **Rule:** Form Verb-Noun Pairs

### audit_codebase
- **File:** `naming_audit.py`
- **Line:** 67
- **Issue:** Function 'audit_codebase' should follow verb-noun pattern
- **Suggested:** `process_audit_codebase`
- **Rule:** Form Verb-Noun Pairs

*... and 759 more medium violations*

## Low Priority Violations

### c
- **File:** `test_autonomous_fast.py`
- **Line:** 54
- **Issue:** Single-letter variable 'c' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### g
- **File:** `test_autonomous_fast.py`
- **Line:** 60
- **Issue:** Single-letter variable 'g' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### f
- **File:** `analyze_functions.py`
- **Line:** 18
- **Issue:** Single-letter variable 'f' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### f
- **File:** `naming_audit.py`
- **Line:** 335
- **Issue:** Single-letter variable 'f' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### f
- **File:** `naming_audit.py`
- **Line:** 341
- **Issue:** Single-letter variable 'f' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### f
- **File:** `naming_audit.py`
- **Line:** 180
- **Issue:** Single-letter variable 'f' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### v
- **File:** `naming_audit.py`
- **Line:** 325
- **Issue:** Single-letter variable 'v' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### v
- **File:** `naming_audit.py`
- **Line:** 368
- **Issue:** Single-letter variable 'v' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### v
- **File:** `naming_audit.py`
- **Line:** 318
- **Issue:** Single-letter variable 'v' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### v
- **File:** `naming_audit.py`
- **Line:** 319
- **Issue:** Single-letter variable 'v' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

*... and 582 more low violations*

