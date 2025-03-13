import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod

from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from .models import Policy, Condition, Action


class PolicyStorage(ABC):
    """Abstract base class for policy storage."""
    
    @abstractmethod
    def get_all_policies(self) -> List[Policy]:
        """Get all policies."""
        pass
    
    @abstractmethod
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a specific policy by ID."""
        pass
    
    @abstractmethod
    def create_policy(self, policy: Policy) -> Policy:
        """Create a new policy."""
        pass
    
    @abstractmethod
    def update_policy(self, policy_id: str, policy_data: Dict) -> Optional[Policy]:
        """Update an existing policy."""
        pass
    
    @abstractmethod
    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy."""
        pass


class InMemoryPolicyStorage(PolicyStorage):
    """In-memory implementation of policy storage."""
    
    def __init__(self):
        self.policies: Dict[str, Policy] = {}
    
    def get_all_policies(self) -> List[Policy]:
        return list(self.policies.values())
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        return self.policies.get(policy_id)
    
    def create_policy(self, policy: Policy) -> Policy:
        if not policy.policy_id:
            policy.policy_id = str(uuid.uuid4())
        policy.created_at = datetime.now()
        self.policies[policy.policy_id] = policy
        return policy
    
    def update_policy(self, policy_id: str, policy_data: Dict) -> Optional[Policy]:
        if policy_id not in self.policies:
            return None
        
        current_policy = self.policies[policy_id]
        
        # Update only the provided fields
        for key, value in policy_data.items():
            if hasattr(current_policy, key) and value is not None:
                setattr(current_policy, key, value)
        
        current_policy.updated_at = datetime.now()
        return current_policy
    
    def delete_policy(self, policy_id: str) -> bool:
        if policy_id in self.policies:
            del self.policies[policy_id]
            return True
        return False


# SQLAlchemy models for SQLite storage
Base = declarative_base()


class ConditionModel(Base):
    __tablename__ = "conditions"
    
    id = Column(Integer, primary_key=True)
    policy_id = Column(String, ForeignKey("policies.policy_id"))
    field = Column(String, nullable=False)
    operator = Column(String, nullable=False)
    value = Column(JSON, nullable=False)


class ActionModel(Base):
    __tablename__ = "actions"
    
    id = Column(Integer, primary_key=True)
    policy_id = Column(String, ForeignKey("policies.policy_id"))
    type = Column(String, nullable=False)
    target = Column(String, nullable=False)
    parameters = Column(JSON, nullable=True)


class PolicyModel(Base):
    __tablename__ = "policies"
    
    policy_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)
    
    conditions = relationship("ConditionModel", cascade="all, delete-orphan")
    actions = relationship("ActionModel", cascade="all, delete-orphan")


class SQLitePolicyStorage(PolicyStorage):
    """SQLite implementation of policy storage."""
    
    def __init__(self, db_path="policies.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def _model_to_policy(self, policy_model: PolicyModel) -> Policy:
        """Convert SQLAlchemy model to Pydantic model."""
        conditions = [
            Condition(field=c.field, operator=c.operator, value=c.value)
            for c in policy_model.conditions
        ]
        
        actions = [
            Action(type=a.type, target=a.target, parameters=a.parameters or {})
            for a in policy_model.actions
        ]
        
        return Policy(
            policy_id=policy_model.policy_id,
            name=policy_model.name,
            description=policy_model.description,
            conditions=conditions,
            actions=actions,
            priority=policy_model.priority,
            enabled=policy_model.enabled,
            created_at=policy_model.created_at,
            updated_at=policy_model.updated_at,
            tags=policy_model.tags or []
        )
    
    def get_all_policies(self) -> List[Policy]:
        session = self.Session()
        try:
            policy_models = session.query(PolicyModel).all()
            return [self._model_to_policy(pm) for pm in policy_models]
        finally:
            session.close()
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        session = self.Session()
        try:
            policy_model = session.query(PolicyModel).get(policy_id)
            if policy_model is None:
                return None
            return self._model_to_policy(policy_model)
        finally:
            session.close()
    
    def create_policy(self, policy: Policy) -> Policy:
        if not policy.policy_id:
            policy.policy_id = str(uuid.uuid4())
        
        session = self.Session()
        try:
            # Create policy model
            policy_model = PolicyModel(
                policy_id=policy.policy_id,
                name=policy.name,
                description=policy.description,
                priority=policy.priority,
                enabled=policy.enabled,
                created_at=datetime.now(),
                tags=policy.tags
            )
            
            # Add conditions
            for condition in policy.conditions:
                condition_model = ConditionModel(
                    field=condition.field,
                    operator=condition.operator,
                    value=condition.value
                )
                policy_model.conditions.append(condition_model)
            
            # Add actions
            for action in policy.actions:
                action_model = ActionModel(
                    type=action.type,
                    target=action.target,
                    parameters=action.parameters
                )
                policy_model.actions.append(action_model)
            
            session.add(policy_model)
            session.commit()
            
            # Return the created policy
            return self._model_to_policy(policy_model)
        finally:
            session.close()
    
    def update_policy(self, policy_id: str, policy_data: Dict) -> Optional[Policy]:
        session = self.Session()
        try:
            policy_model = session.query(PolicyModel).get(policy_id)
            if policy_model is None:
                return None
            
            # Update basic fields
            for key, value in policy_data.items():
                if key not in ["conditions", "actions"] and hasattr(policy_model, key) and value is not None:
                    setattr(policy_model, key, value)
            
            # Update conditions if provided
            if "conditions" in policy_data and policy_data["conditions"] is not None:
                # Remove existing conditions
                for condition in policy_model.conditions:
                    session.delete(condition)
                
                # Add new conditions
                for condition in policy_data["conditions"]:
                    condition_model = ConditionModel(
                        policy_id=policy_id,
                        field=condition.field,
                        operator=condition.operator,
                        value=condition.value
                    )
                    session.add(condition_model)
            
            # Update actions if provided
            if "actions" in policy_data and policy_data["actions"] is not None:
                # Remove existing actions
                for action in policy_model.actions:
                    session.delete(action)
                
                # Add new actions
                for action in policy_data["actions"]:
                    action_model = ActionModel(
                        policy_id=policy_id,
                        type=action.type,
                        target=action.target,
                        parameters=action.parameters
                    )
                    session.add(action_model)
            
            policy_model.updated_at = datetime.now()
            session.commit()
            
            return self._model_to_policy(policy_model)
        finally:
            session.close()
    
    def delete_policy(self, policy_id: str) -> bool:
        session = self.Session()
        try:
            policy_model = session.query(PolicyModel).get(policy_id)
            if policy_model is None:
                return False
            
            session.delete(policy_model)
            session.commit()
            return True
        finally:
            session.close()


def get_policy_storage(storage_type: str = "memory", **kwargs) -> PolicyStorage:
    """Factory function to create policy storage."""
    if storage_type == "memory":
        return InMemoryPolicyStorage()
    elif storage_type == "sqlite":
        db_path = kwargs.get("db_path", "policies.db")
        return SQLitePolicyStorage(db_path=db_path)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}") 