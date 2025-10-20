# Naming Violations Report

**Generated:** Tue Oct 14 12:04:20 PM CEST 2025

## Summary

- **Total Violations:** 942
- **Critical:** 0
- **High:** 80
- **Medium:** 249
- **Low:** 613

## Violations by Type

- **Directory Plural:** 71
- **Directory Ambiguous:** 1
- **Directory Deep Nesting:** 5
- **Variable Single Letter:** 613
- **Function No Verb Noun:** 225
- **Function Boolean Flag:** 7
- **File Not Snake Case:** 3
- **Variable Hungarian Notation:** 16
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

*... and 70 more high violations*

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

### cli
- **File:** `autonomous_dev_tool.py`
- **Line:** 661
- **Issue:** Function 'cli' should follow verb-noun pattern
- **Suggested:** `process_cli`
- **Rule:** Form Verb-Noun Pairs

### status
- **File:** `autonomous_dev_tool.py`
- **Line:** 838
- **Issue:** Function 'status' should follow verb-noun pattern
- **Suggested:** `get_status`
- **Rule:** Form Verb-Noun Pairs

### redis_config
- **File:** `tests/conftest.py`
- **Line:** 13
- **Issue:** Function 'redis_config' should follow verb-noun pattern
- **Suggested:** `configure_redis_config`
- **Rule:** Form Verb-Noun Pairs

### short_ttl_config
- **File:** `tests/conftest.py`
- **Line:** 25
- **Issue:** Function 'short_ttl_config' should follow verb-noun pattern
- **Suggested:** `configure_short_ttl_config`
- **Rule:** Form Verb-Noun Pairs

### demo_parse_and_execute
- **File:** `examples/dsl_example.py`
- **Line:** 76
- **Issue:** Function 'demo_parse_and_execute' should follow verb-noun pattern
- **Suggested:** `process_demo_parse_and_execute`
- **Rule:** Form Verb-Noun Pairs

*... and 239 more medium violations*

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
- **Line:** 543
- **Issue:** Single-letter variable 'f' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### f
- **File:** `naming_audit.py`
- **Line:** 549
- **Issue:** Single-letter variable 'f' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### f
- **File:** `naming_audit.py`
- **Line:** 298
- **Issue:** Single-letter variable 'f' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### v
- **File:** `naming_audit.py`
- **Line:** 533
- **Issue:** Single-letter variable 'v' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### v
- **File:** `naming_audit.py`
- **Line:** 576
- **Issue:** Single-letter variable 'v' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### v
- **File:** `naming_audit.py`
- **Line:** 526
- **Issue:** Single-letter variable 'v' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

### v
- **File:** `naming_audit.py`
- **Line:** 527
- **Issue:** Single-letter variable 'v' should have descriptive name
- **Suggested:** `Use descriptive name based on purpose`
- **Rule:** Scale Length with Scope

*... and 603 more low violations*

