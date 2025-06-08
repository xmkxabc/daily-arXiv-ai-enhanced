from pydantic import BaseModel, Field
# Correctly import Optional from the standard typing library
from typing import Optional

class Structure(BaseModel):
    """
    The structured data for a paper, including a newly generated summary and translation.
    """
    tldr: Optional[str] = Field(default=None, description="generate a too long; didn't read summary")
    motivation: Optional[str] = Field(default=None, description="describe the motivation in this paper")
    method: Optional[str] = Field(default=None, description="method of this paper")
    result: Optional[str] = Field(default=None, description="result of this paper")
    conclusion: Optional[str] = Field(default=None, description="conclusion of this paper")
    translation: Optional[str] = Field(default=None, description="translate the paper to Chinese")
    summary: Optional[str] = Field(default=None, description="generate a new, concise summary of the paper based on its abstract")
