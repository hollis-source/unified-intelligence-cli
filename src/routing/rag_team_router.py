"""
RAG-Enhanced Team Router - Routes tasks using historical patterns.

Phase 2: RAG-enhanced routing that retrieves similar successful patterns
before making routing decisions.

Clean Architecture: Decorator pattern over TeamRouter.
"""

import logging
import json
from typing import List, Optional, Dict, Any
from src.entity import Task, Agent, AgentTeam
from src.routing.team_router import TeamRouter
from src.routing.domain_classifier import DomainClassifier


logger = logging.getLogger(__name__)


class RAGTeamRouter(TeamRouter):
    """
    RAG-enhanced team router that uses historical patterns for better routing.
    
    Enhancement Strategy:
        1. Retrieve similar successful patterns from SurrealDB
        2. Use patterns to inform routing decision
        3. Fallback to base TeamRouter if no patterns or RAG unavailable
        4. Track routing decisions for feedback loop
    
    Benefits:
        - Learn from historical successes
        - Adapt routing based on actual outcomes
        - Improve accuracy over time
        - Maintain compatibility with base router
    
    Clean Code: Decorator pattern - extends TeamRouter without modifying it.
    """
    
    def __init__(
        self,
        domain_classifier: Optional[DomainClassifier] = None,
        db_store: Optional[Any] = None,
        embedding_pipeline: Optional[Any] = None,
        top_k: int = 3,
        similarity_threshold: float = 0.5,
        use_rag: bool = True
    ):
        """
        Initialize RAG-enhanced team router.
        
        Args:
            domain_classifier: Classifier for domain detection
            db_store: SurrealDBStore for pattern retrieval
            embedding_pipeline: EmbeddingPipeline for query embeddings
            top_k: Number of similar patterns to retrieve
            similarity_threshold: Minimum similarity score (0-1)
            use_rag: Enable/disable RAG (for A/B testing)
        """
        super().__init__(domain_classifier)
        
        self.db_store = db_store
        self.embedding_pipeline = embedding_pipeline
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.use_rag = use_rag and db_store is not None and embedding_pipeline is not None
        
        if self.use_rag:
            logger.info(f"RAGTeamRouter initialized (top_k={top_k}, threshold={similarity_threshold})")
        else:
            logger.info("RAGTeamRouter initialized (RAG disabled, using base routing)")
    
    async def route_with_rag(self, task: Task, teams: List[AgentTeam]) -> Agent:
        """
        Route task using RAG-enhanced decision making.

        Strategy:
            1. Generate embedding for task description
            2. Retrieve top-K similar successful patterns
            3. Analyze patterns to inform routing
            4. Make routing decision (RAG-informed or fallback)
            5. Track decision for feedback

        Args:
            task: Task to route
            teams: Available teams

        Returns:
            Selected agent
        """
        if not self.use_rag:
            # RAG disabled, use base routing
            agent = self.route(task, teams)

            # Feature flag: Track baseline routing decisions
            # Enables A/B test source count analysis when RAG is disabled
            import os
            if os.getenv("RAG_BASELINE_TRACK_DECISIONS") == "1":
                try:
                    await self._track_routing_decision(
                        task=task,
                        selected_agent=agent,
                        patterns_used=[],
                        routing_hints={},
                        strategy="baseline",
                        fallback_used=False
                    )
                except Exception as e:
                    logger.debug(f"Baseline tracking failed (non-critical): {e}")

            return agent
        
        try:
            # Step 1: Retrieve similar patterns
            patterns = await self._retrieve_similar_patterns(task)

            if not patterns:
                logger.debug("No similar patterns found, using base routing and tracking decision")
                agent = self.route(task, teams)
                try:
                    await self._track_routing_decision(
                        task=task,
                        selected_agent=agent,
                        patterns_used=[],
                        routing_hints={},
                        strategy="fallback",
                        fallback_used=True,
                    )
                except Exception:
                    pass
                return agent

            # Step 2: Analyze patterns for routing hints
            routing_hints = self._analyze_patterns(patterns)

            # Step 3: Make RAG-informed routing decision
            agent = self._route_with_hints(task, teams, routing_hints)
            
            # Step 4: Track routing decision
            await self._track_routing_decision(
                task=task,
                selected_agent=agent,
                patterns_used=patterns,
                routing_hints=routing_hints,
                strategy="rag"
            )
            
            return agent
            
        except Exception as e:
            logger.warning(f"RAG routing failed: {e}. Falling back to base routing.")
            # Fallback to base routing
            agent = self.route(task, teams)
            
            # Track fallback decision
            try:
                await self._track_routing_decision(
                    task=task,
                    selected_agent=agent,
                    patterns_used=[],
                    routing_hints={},
                    strategy="fallback",
                    fallback_used=True
                )
            except Exception:
                pass  # Don't fail routing due to tracking errors
            
            return agent
    
    async def _retrieve_similar_patterns(self, task: Task) -> List[Dict[str, Any]]:
        """
        Retrieve similar successful execution patterns.
        
        Args:
            task: Task to find patterns for
            
        Returns:
            List of similar patterns with metadata
        """
        try:
            # Generate embedding for task
            query_text = f"Task: {task.description}"
            query_embedding = await self.embedding_pipeline.embed_text(query_text)
            
            # Search for similar successful executions
            patterns = await self.db_store.search_similar_execution(
                query_embedding=query_embedding,
                top_k=self.top_k,
                domain=None,  # Search across all domains
                success_only=True  # Only successful patterns
            )
            
            # Filter by similarity threshold
            filtered = [
                p for p in patterns
                if p.get('similarity', 0) >= self.similarity_threshold
            ]
            
            logger.debug(f"Retrieved {len(filtered)} similar patterns (threshold={self.similarity_threshold})")
            
            return filtered
            
        except Exception as e:
            logger.warning(f"Failed to retrieve patterns: {e}")
            return []
    
    def _analyze_patterns(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze patterns to extract routing hints.
        
        Args:
            patterns: Similar successful patterns
            
        Returns:
            Dict with routing hints (agent_role, team, confidence, etc.)
        """
        if not patterns:
            return {}
        
        # Count agent roles in successful patterns
        agent_counts = {}
        team_counts = {}
        domain_counts = {}
        
        for pattern in patterns:
            agent_role = pattern.get('agent_role')
            team_id = pattern.get('team_id')
            domain = pattern.get('task_domain')
            similarity = pattern.get('similarity', 0)
            
            if agent_role:
                agent_counts[agent_role] = agent_counts.get(agent_role, 0) + similarity
            if team_id:
                team_counts[team_id] = team_counts.get(team_id, 0) + similarity
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + similarity
        
        # Find most common (weighted by similarity)
        best_agent = max(agent_counts.items(), key=lambda x: x[1])[0] if agent_counts else None
        best_team = max(team_counts.items(), key=lambda x: x[1])[0] if team_counts else None
        best_domain = max(domain_counts.items(), key=lambda x: x[1])[0] if domain_counts else None
        
        # Calculate confidence (average similarity of top patterns)
        avg_similarity = sum(p.get('similarity', 0) for p in patterns) / len(patterns)
        
        hints = {
            'suggested_agent': best_agent,
            'suggested_team': best_team,
            'suggested_domain': best_domain,
            'confidence': avg_similarity,
            'pattern_count': len(patterns),
            'agent_distribution': agent_counts,
            'team_distribution': team_counts
        }
        
        logger.debug(f"Routing hints: agent={best_agent}, team={best_team}, confidence={avg_similarity:.2f}")
        
        return hints
    
    def _route_with_hints(
        self,
        task: Task,
        teams: List[AgentTeam],
        hints: Dict[str, Any]
    ) -> Agent:
        """
        Make routing decision using hints from patterns.
        
        Strategy:
            1. If high confidence (>0.7) and agent exists, use suggested agent
            2. If medium confidence (>0.5) and team exists, route to suggested team
            3. Otherwise, fallback to base routing
        
        Args:
            task: Task to route
            teams: Available teams
            hints: Routing hints from pattern analysis
            
        Returns:
            Selected agent
        """
        confidence = hints.get('confidence', 0)
        suggested_agent = hints.get('suggested_agent')
        suggested_team = hints.get('suggested_team')
        
        # High confidence: Try to use exact agent
        if confidence > 0.7 and suggested_agent:
            agent = self._find_agent_by_role(teams, suggested_agent)
            if agent:
                logger.info(f"RAG routing (high confidence): {suggested_agent} (confidence={confidence:.2f})")
                return agent
        
        # Medium confidence: Route to suggested team
        if confidence > 0.5 and suggested_team:
            team = self._get_team_by_name(teams, suggested_team)
            if team:
                agent = team.route_internally(task)
                logger.info(f"RAG routing (medium confidence): {suggested_team} → {agent.role} (confidence={confidence:.2f})")
                return agent
        
        # Low confidence or no match: Fallback to base routing
        logger.debug(f"RAG routing (low confidence): using base routing (confidence={confidence:.2f})")
        return self.route(task, teams)
    
    def _find_agent_by_role(self, teams: List[AgentTeam], role: str) -> Optional[Agent]:
        """Find agent by role across all teams."""
        for team in teams:
            for agent in team.agents:
                if agent.role == role:
                    return agent
        return None
    
    async def _track_routing_decision(
        self,
        task: Task,
        selected_agent: Agent,
        patterns_used: List[Dict[str, Any]],
        routing_hints: Dict[str, Any],
        strategy: str,
        fallback_used: bool = False
    ):
        """
        Track routing decision for feedback loop.
        
        Args:
            task: Task that was routed
            selected_agent: Agent selected for task
            patterns_used: Patterns that informed decision
            routing_hints: Hints extracted from patterns
            strategy: Routing strategy used ('rag', 'fallback', etc.)
            fallback_used: Whether fallback was used
        """
        try:
            if not self.db_store:
                return
            
            import uuid
            
            await self.db_store.store_routing_decision(
                task_id=task.task_id,
                task_description=task.description,
                task_domain=self._last_classified_domain,
                selected_agent=selected_agent.role,
                selected_team=None,  # TODO: Get team name
                routing_strategy=strategy,
                confidence=routing_hints.get('confidence', 0.0),
                success=None,  # Will be updated after execution
                actual_agent=selected_agent.role,
                fallback_used=fallback_used,
                metadata={
                    'rag_used': (strategy == 'rag'),
                    'pattern_count': len(patterns_used),
                    'routing_hints': routing_hints,
                    'top_patterns': [
                        {
                            'agent': p.get('agent_role'),
                            'similarity': p.get('similarity')
                        }
                        for p in patterns_used[:3]
                    ]
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to track routing decision: {e}")

