"""
Product Request router — catalogue + farmer orders.
(Similar to Service Requests but for physical goods like seeds/fertilizer).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.service_request import Product, ProductRequest
from models.farm import Farm
from models.user import User
from schemas.service_request import (
    CreateProductRequest, ProductResponse, ProductRequestResponse,
)
from dependencies import authorize, get_current_user
from enums import UserRole
from exceptions import NotFoundError

router = APIRouter(prefix="/product", tags=["Product Requests"])


@router.get("/", response_model=list[ProductResponse])
def get_product_catalogue(db: Session = Depends(get_db)):
    """List all active products."""
    return db.query(Product).filter(Product.isActive == True).all()


@router.post("/{product_id}/request", response_model=ProductRequestResponse)
def create_product_request(
    product_id: int,
    body: CreateProductRequest,
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.PROGRESSIVE_FARMER, UserRole.ADMIN)),
):
    """Farmer submits a new product order."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product", product_id)

    farm = db.query(Farm).filter(Farm.id == body.farmId).first()
    if not farm:
        raise NotFoundError("Farm", body.farmId)

    req = ProductRequest(
        farmId=body.farmId,
        productId=product_id,
        quantity=body.quantity,
        notes=body.notes,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return db.query(ProductRequest).options(
        joinedload(ProductRequest.farm),
        joinedload(ProductRequest.product)
    ).filter(ProductRequest.id == req.id).first()


@router.get("/requests/service-center/{center_id}", response_model=list[ProductRequestResponse])
def get_manager_product_queue(
    center_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Manager views all product requests for farms in their center."""
    reqs = (
        db.query(ProductRequest)
        .join(Farm, ProductRequest.farmId == Farm.id)
        .options(
            joinedload(ProductRequest.farm),
            joinedload(ProductRequest.product)
        )
        .filter(Farm.serviceCenterId == center_id)
        .order_by(ProductRequest.requestedAt.desc())
        .all()
    )
    return reqs
