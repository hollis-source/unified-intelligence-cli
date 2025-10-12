# CI/CD Integration Examples

Integrate Unified Intelligence CLI into your CI/CD pipelines for automated AI-powered tasks.

## Table of Contents

- [GitHub Actions](#github-actions)
- [GitLab CI](#gitlab-ci)
- [Jenkins](#jenkins)
- [CircleCI](#circleci)
- [Azure DevOps](#azure-devops)

## GitHub Actions

### Basic Workflow

```yaml
# .github/workflows/ai-tasks.yml
name: AI Tasks

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  ai-analysis:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    
    - name: Install UI-CLI
      run: |
        pip install unified-intelligence-cli
    
    - name: Run AI Analysis
      env:
        XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
      run: |
        ui-cli \
          "Analyze: Review code structure in the repository" \
          "Recommendations: Suggest 3 improvements" \
          "Priority: Rank recommendations by impact"
    
    - name: Save Results
      run: |
        ui-cli --output json \
          "Generate: Create summary report" \
          > analysis-results.json
    
    - name: Upload Results
      uses: actions/upload-artifact@v3
      with:
        name: ai-analysis
        path: analysis-results.json
```

### Code Review Bot

```yaml
# .github/workflows/ai-code-review.yml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Get Changed Files
      id: changes
      run: |
        git diff --name-only origin/${{ github.base_ref }}...${{ github.head_ref }} > changed_files.txt
        echo "Files changed:"
        cat changed_files.txt
    
    - name: Install UI-CLI
      run: pip install unified-intelligence-cli
    
    - name: AI Code Review
      env:
        XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
      run: |
        REVIEW=$(ui-cli --output json \
          "Review: Analyze the following changed files: $(cat changed_files.txt)" \
          "Quality: Rate code quality (1-10) and explain" \
          "Issues: List potential bugs or improvements" \
          "Security: Identify security concerns")
        
        echo "$REVIEW" > review.json
    
    - name: Post Review Comment
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          const review = JSON.parse(fs.readFileSync('review.json', 'utf8'));
          
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: `## AI Code Review\n\n${review.results.join('\n\n')}`
          });
```

### Docker Build Workflow

```yaml
# .github/workflows/ai-docker-build.yml
name: AI-Enhanced Docker Build

on:
  push:
    branches: [ main ]

jobs:
  analyze-and-build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install UI-CLI
      run: pip install unified-intelligence-cli
    
    - name: Analyze Dockerfile
      env:
        XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
      run: |
        ui-cli \
          "Review: Analyze the Dockerfile for best practices" \
          "Security: Check for security vulnerabilities" \
          "Optimize: Suggest optimization strategies"
    
    - name: Build Docker Image
      run: docker build -t myapp:latest .
    
    - name: Push to Registry
      if: success()
      run: docker push myapp:latest
```

## GitLab CI

### .gitlab-ci.yml

```yaml
stages:
  - analyze
  - test
  - deploy

variables:
  UI_CLI_VERSION: "1.0.0"

before_script:
  - pip install unified-intelligence-cli==$UI_CLI_VERSION

ai-analysis:
  stage: analyze
  image: python:3.12-slim
  script:
    - ui-cli --output json \
        "Analyze: Review project structure" \
        "Security: Check for vulnerabilities" \
        > analysis.json
  artifacts:
    reports:
      dotenv: analysis.json
    paths:
      - analysis.json
    expire_in: 1 week
  only:
    - merge_requests
    - main

ai-code-review:
  stage: analyze
  image: python:3.12-slim
  script:
    - |
      git diff origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME...HEAD > changes.patch
      ui-cli \
        "Review: Analyze the code changes in changes.patch" \
        "Issues: List potential problems" \
        "Rating: Rate quality (1-10)"
  only:
    - merge_requests

ai-test-generation:
  stage: test
  image: python:3.12-slim
  script:
    - ui-cli \
        "Generate: Create unit tests for new functions" \
        "Coverage: Identify untested code paths"
  only:
    - merge_requests
```

## Jenkins

### Jenkinsfile

```groovy
pipeline {
    agent any
    
    environment {
        XAI_API_KEY = credentials('xai-api-key')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install unified-intelligence-cli'
            }
        }
        
        stage('AI Analysis') {
            steps {
                script {
                    def analysis = sh(
                        script: '''
                            ui-cli --output json \
                                "Analyze: Review codebase structure" \
                                "Issues: Identify potential problems"
                        ''',
                        returnStdout: true
                    ).trim()
                    
                    writeFile file: 'analysis.json', text: analysis
                    archiveArtifacts artifacts: 'analysis.json'
                }
            }
        }
        
        stage('Code Review') {
            when {
                changeRequest()
            }
            steps {
                sh '''
                    ui-cli \
                        "Review: Analyze PR changes" \
                        "Quality: Rate code quality" \
                        "Recommendations: Suggest improvements"
                '''
            }
        }
        
        stage('Test') {
            steps {
                sh 'pytest tests/'
            }
        }
        
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    ui-cli \
                        "PreDeploy: Checklist for deployment" \
                        "Verify: Check configuration"
                '''
                sh 'docker build -t myapp:latest .'
                sh 'docker push myapp:latest'
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            sh 'ui-cli "Success: Document successful deployment"'
        }
        failure {
            sh 'ui-cli "Failure: Analyze build failure and suggest fixes"'
        }
    }
}
```

## CircleCI

### .circleci/config.yml

```yaml
version: 2.1

executors:
  python-executor:
    docker:
      - image: cimg/python:3.12

jobs:
  ai-analysis:
    executor: python-executor
    steps:
      - checkout
      
      - run:
          name: Install UI-CLI
          command: pip install unified-intelligence-cli
      
      - run:
          name: Run AI Analysis
          command: |
            ui-cli --output json \
              "Analyze: Review project structure" \
              "Security: Check for security issues" \
              > analysis.json
      
      - store_artifacts:
          path: analysis.json
      
      - persist_to_workspace:
          root: .
          paths:
            - analysis.json

  ai-code-review:
    executor: python-executor
    steps:
      - checkout
      
      - run:
          name: Install UI-CLI
          command: pip install unified-intelligence-cli
      
      - run:
          name: AI Code Review
          command: |
            git diff origin/main...HEAD > changes.diff
            ui-cli \
              "Review: Analyze changes in changes.diff" \
              "Rate: Code quality score (1-10)" \
              "Issues: List potential problems"

  deploy:
    executor: python-executor
    steps:
      - checkout
      
      - setup_remote_docker:
          docker_layer_caching: true
      
      - run:
          name: Build and Push Docker
          command: |
            docker build -t myapp:latest .
            docker push myapp:latest

workflows:
  version: 2
  ai-enhanced-pipeline:
    jobs:
      - ai-analysis
      - ai-code-review:
          filters:
            branches:
              ignore: main
      - deploy:
          requires:
            - ai-analysis
          filters:
            branches:
              only: main
```

## Azure DevOps

### azure-pipelines.yml

```yaml
trigger:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  pythonVersion: '3.12'

stages:
- stage: Analyze
  jobs:
  - job: AIAnalysis
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: '$(pythonVersion)'
    
    - script: |
        pip install unified-intelligence-cli
      displayName: 'Install UI-CLI'
    
    - script: |
        ui-cli --output json \
          "Analyze: Review Azure DevOps pipeline configuration" \
          "Security: Check for security issues" \
          > $(Build.ArtifactStagingDirectory)/analysis.json
      env:
        XAI_API_KEY: $(XAI_API_KEY)
      displayName: 'Run AI Analysis'
    
    - task: PublishBuildArtifacts@1
      inputs:
        pathToPublish: '$(Build.ArtifactStagingDirectory)'
        artifactName: 'ai-analysis'

- stage: Review
  condition: eq(variables['Build.Reason'], 'PullRequest')
  jobs:
  - job: CodeReview
    steps:
    - script: |
        pip install unified-intelligence-cli
        ui-cli \
          "Review: Analyze PR changes" \
          "Quality: Rate code quality" \
          "Suggestions: List improvements"
      env:
        XAI_API_KEY: $(XAI_API_KEY)
      displayName: 'AI Code Review'

- stage: Deploy
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  jobs:
  - deployment: DeployToProduction
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - script: |
              ui-cli "PreDeploy: Generate deployment checklist"
            env:
              XAI_API_KEY: $(XAI_API_KEY)
            displayName: 'Pre-deployment Check'
          
          - task: Docker@2
            inputs:
              command: 'buildAndPush'
              repository: 'myapp'
              tags: 'latest'
```

## Best Practices

### 1. Secure API Keys

**GitHub Actions:**
```yaml
env:
  XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
```

**GitLab CI:**
```yaml
variables:
  XAI_API_KEY:
    value: $XAI_API_KEY
    description: "xAI API Key"
```

**Jenkins:**
```groovy
environment {
    XAI_API_KEY = credentials('xai-api-key')
}
```

### 2. Cache Dependencies

**GitHub Actions:**
```yaml
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

**GitLab CI:**
```yaml
cache:
  paths:
    - .pip-cache/
```

### 3. Fail Fast

```yaml
- name: Critical Analysis
  run: |
    ui-cli "Security: Check for critical vulnerabilities"
  continue-on-error: false
```

### 4. Parallel Execution

**GitHub Actions:**
```yaml
strategy:
  matrix:
    task: [analyze, review, test]
```

**GitLab CI:**
```yaml
parallel:
  matrix:
    - TASK: [analyze, review, test]
```

## Monitoring and Notifications

### Slack Integration (GitHub Actions)

```yaml
- name: Notify Slack
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'AI Analysis completed'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Email Notifications (Jenkins)

```groovy
post {
    failure {
        emailext (
            subject: "AI Pipeline Failed: ${env.JOB_NAME}",
            body: "Check console output at ${env.BUILD_URL}",
            to: "team@example.com"
        )
    }
}
```

---

**Last Updated:** 2025-09-30
**Version:** 1.0.0
