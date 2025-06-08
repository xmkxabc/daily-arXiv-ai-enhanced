from pydantic import BaseModel, Field
from typing import Optional

class Structure(BaseModel):
    """
    The structured data for a paper.
    """
    # 强制要求AI必须提供tldr
    tldr: Optional[str] = Field(default=None, description="You MUST provide a one-sentence summary (TL;DR) of the paper. This is a mandatory field. Use {language}.")
    
    motivation: Optional[str] = Field(default=None, description="What problem is the paper trying to solve? If not mentioned in the abstract, state 'Not mentioned in abstract'. Please answer in {language}.")
    
    method: Optional[str] = Field(default=None, description="How did the paper solve the problem? What is the proposed method? If not mentioned in the abstract, state 'Not mentioned in abstract'. Please answer in {language}.")
    
    result: Optional[str] = Field(default=None, description="What are the main results of the paper? If not mentioned in the abstract, state 'Not mentioned in abstract'. Please answer in {language}.")
    
    conclusion: Optional[str] = Field(default=None, description="What are the main conclusions of the paper? What are the implications of this work? If not mentioned in the abstract, state 'Not mentioned in abstract'. Please answer in {language}.")
    
    translation: Optional[str] = Field(default=None, description="Translate the abstract into {language}. This is a mandatory field.")
    
    related_work: Optional[str] = Field(default=None, description="What related work is compared or connected to in this paper? If not mentioned in the abstract, state 'Not mentioned in abstract'. Please answer in {language}.")
    
    potential_applications: Optional[str] = Field(default=None, description="What are the potential application scenarios for this research? If not mentioned in the abstract, state 'Not mentioned in abstract'. Please answer in {language}.")
    
    future_work: Optional[str] = Field(default=None, description="What does the paper suggest for future work? If not mentioned in the abstract, state 'Not mentioned in abstract'. Please answer in {language}.")
