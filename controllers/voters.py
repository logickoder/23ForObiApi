from typing import List

import fastapi
import sqlalchemy.orm as Session
from bigfastapi.db.database import get_db
from bigfastapi.schemas import users_schemas
from fastapi import APIRouter
from models import village_models, voter_models
from schemas import voter_schemas

app = APIRouter()


@app.get("/voters/{village_id}", response_model=List[voter_schemas.VoterSchema])
async def list_voters_in_a_village(
    village_id: str, db: Session = fastapi.Depends(get_db)
):
    voters = db.query(voter_models.Voter).filter(
        voter_models.Voter.village == village_id
    )

    return list(map(voter_schemas.VoterSchema.from_orm, voters))


@app.post("/voters")
async def add_voters_to_village(
    voter: voter_schemas.VoterSchemaBase, db: Session = fastapi.Depends(get_db)
):
    db_voters_to_village = voter_models.Voter(
        name=voter.name,
        village=voter.village,
        contact=voter.contact,
        notes=voter.notes,
        importance=voter.importance,
    )

    # check if village exist
    try:
        db.query(village_models.Village).get(village_models.Village.id == voter.village)
    except Exception as e:
        raise fastapi.HTTPException(status_code=400, detail="Village does not exist")

    db.add(db_voters_to_village)
    db.commit()
    db.refresh(db_voters_to_village)
    return {
        "message": "Support Group created succesfully",
        "support_group": voter_schemas.VoterSchema.from_orm(db_voters_to_village),
    }