from pydantic import BaseModel, Field
from typing import Optional

class Structure(BaseModel):
    """
    The structured data for a paper.
    """
    tldr: Optional[str] = Field(default=None, description="A one-sentence summary of the paper, in {language}.")
    motivation: Optional[str] = Field(default=None, description="What problem is the paper trying to solve? What is the motivation for this work? Please answer in {language}.")
    method: Optional[str] = Field(default=None, description="How did the paper solve the problem? What is the proposed method? Please answer in {language}.")
    result: Optional[str] = Field(default=None, description="What are the main results of the paper? Please answer in {language}.")
    conclusion: Optional[str] = Field(default=None, description="What are the main conclusions of the paper? What are the implications of this work? Please answer in {language}.")
