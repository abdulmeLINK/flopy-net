"""
Policy Engine API

This module provides a simple policy engine API for demonstration purposes.
"""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Create FastAPI app
app = FastAPI(title="Policy Engine API", version="1.0.0")

# Sample data
policies = []


class Policy(BaseModel):
    """Policy model."""
    id: Optional[int] = None
    name: str
    description: str
    rules: List[Dict[str, Any]]
    enabled: bool = True


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Policy Engine API", "version": "1.0.0"}


@app.get("/policies")
async def get_policies():
    """Get all policies."""
    return policies


@app.post("/policies", status_code=201)
async def create_policy(policy: Policy):
    """Create a new policy."""
    policy_dict = policy.dict()
    policy_dict["id"] = len(policies) + 1
    policies.append(policy_dict)
    return policy_dict


@app.get("/policies/{policy_id}")
async def get_policy(policy_id: int):
    """Get a policy by ID."""
    for policy in policies:
        if policy["id"] == policy_id:
            return policy
    raise HTTPException(status_code=404, detail="Policy not found")


@app.put("/policies/{policy_id}")
async def update_policy(policy_id: int, policy: Policy):
    """Update a policy."""
    for i, p in enumerate(policies):
        if p["id"] == policy_id:
            policy_dict = policy.dict()
            policy_dict["id"] = policy_id
            policies[i] = policy_dict
            return policy_dict
    raise HTTPException(status_code=404, detail="Policy not found")


@app.delete("/policies/{policy_id}")
async def delete_policy(policy_id: int):
    """Delete a policy."""
    for i, policy in enumerate(policies):
        if policy["id"] == policy_id:
            del policies[i]
            return {"message": f"Policy {policy_id} deleted"}
    raise HTTPException(status_code=404, detail="Policy not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 