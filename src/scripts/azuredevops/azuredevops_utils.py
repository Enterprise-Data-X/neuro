#!/usr/bin/env python3
"""Shared Azure DevOps helpers for skill install scripts."""

from __future__ import annotations

import base64
import os
import urllib.request


def ado_request(url: str) -> bytes:
    """
    Performs a request to Azure DevOps API.
    Uses 'AZURE_DEVOPS_EXT_PAT' or 'ADO_TOKEN' for authentication.
    """
    headers = {}
    
    # ADO uses Personal Access Tokens (PAT)
    # The PAT must be Base64 encoded as ":{token}" for the Authorization header
    token = os.environ.get("AZURE_DEVOPS_EXT_PAT") or os.environ.get("ADO_TOKEN")
    
    if token:
        # Azure DevOps PAT authentication requires "Basic" auth with an empty username
        auth_str = f":{token}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        headers["Authorization"] = f"Basic {encoded_auth}"
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def ado_api_items_url(org: str, project: str, repo: str, path: str, ref: str) -> str:
    """
    Builds the URL to get item metadata or content from an ADO Git repo.
    Note: ADO uses 'versionDescriptor' instead of simple 'ref' queries for Git.
    """
    base = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/items"
    query = (
        f"?path={path}"
        f"&versionDescriptor[version]={ref}"
        f"&api-version=7.1"
    )
    return base + query