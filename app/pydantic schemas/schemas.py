from pydantic import BaseModel, EmailStr, AnyUrl, Field, field_validator
from typing import Optional, List, Dict, Annotated

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str
    
    
    
class patientCreate(BaseModel):
    name: str=Field(..., example="John Doe")    
    age:  int=Field(..., example=30, gt=0, lt=150)
    medical_history: str
    married: Optional[bool] = Field(default=False, example=True)
    contact_detail: dict[str, str] = Field(default={}, example={"phone": "123-456-7890", "address": "123 Main St"})
    email: EmailStr
    website: Optional[AnyUrl] = Field(default=None, example="https://www.example.com", description="Patient's personal website or profile")
    names = Annotated[List[str], Field(default_factory=list, example=["John", "Doe"], description="List of patient's names, including first name and last name")]



    # Field validation 
    
    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Age must be between 0 and 150')
        return v
    
    
    @field_validator('contact_detail')
    @classmethod
    def validate_contact_detail(cls, v):
        valid_domains = ["gmail.com", "yahoo.com", "hotmail.com"]
        domain_name = v.split('@')[-1] if '@' in v else None
        if domain_name and domain_name not in valid_domains:
            raise ValueError(f'Email domain must be one of the following: {", ".join(valid_domains)}')
        return v