"""
Atlas – SQLAlchemy ORM Models
Mirrors the warehouse.* schema for use by the API layer and analytics engine.
These are READ models — mutations happen via ETL scripts, not the ORM.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (BigInteger, Boolean, Column, Date, DateTime, ForeignKey,
                        Integer, JSON, Numeric, SmallInteger, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class DimDate(Base):
    __tablename__ = "dim_date"
    __table_args__ = {"schema": "warehouse"}

    date_key         = Column(Integer, primary_key=True)
    full_date        = Column(Date, nullable=False, unique=True)
    day_of_week      = Column(SmallInteger, nullable=False)
    day_name         = Column(String(10), nullable=False)
    day_of_month     = Column(SmallInteger, nullable=False)
    day_of_year      = Column(SmallInteger, nullable=False)
    week_of_year     = Column(SmallInteger, nullable=False)
    month_number     = Column(SmallInteger, nullable=False)
    month_name       = Column(String(10), nullable=False)
    month_short      = Column(String(3), nullable=False)
    quarter          = Column(SmallInteger, nullable=False)
    quarter_label    = Column(String(6), nullable=False)
    year             = Column(SmallInteger, nullable=False)
    is_weekend       = Column(Boolean, nullable=False, default=False)
    is_month_start   = Column(Boolean, nullable=False, default=False)
    is_month_end     = Column(Boolean, nullable=False, default=False)
    fiscal_year      = Column(SmallInteger, nullable=False)
    fiscal_quarter   = Column(SmallInteger, nullable=False)


class DimCountry(Base):
    __tablename__ = "dim_country"
    __table_args__ = {"schema": "warehouse"}

    country_id          = Column(Integer, primary_key=True, autoincrement=True)
    country_code        = Column(String(2), nullable=False, unique=True)
    country_name        = Column(String(100), nullable=False)
    region              = Column(String(50), nullable=False)
    sub_region          = Column(String(50))
    currency_code       = Column(String(3), nullable=False)
    currency_factor     = Column(Numeric(10, 6), nullable=False, default=1.0)
    is_active           = Column(Boolean, nullable=False, default=True)
    gdp_per_capita_band = Column(String(20))
    created_at          = Column(DateTime, nullable=False, default=datetime.now)


class DimChannel(Base):
    __tablename__ = "dim_channel"
    __table_args__ = {"schema": "warehouse"}

    channel_id      = Column(Integer, primary_key=True, autoincrement=True)
    channel_code    = Column(String(30), nullable=False, unique=True)
    channel_name    = Column(String(100), nullable=False)
    campaign_type   = Column(String(50), nullable=False)
    is_paid         = Column(Boolean, nullable=False, default=False)
    avg_cac_gbp     = Column(Numeric(8, 2))
    is_active       = Column(Boolean, nullable=False, default=True)


class DimProduct(Base):
    __tablename__ = "dim_product"
    __table_args__ = {"schema": "warehouse"}

    product_id       = Column(Integer, primary_key=True, autoincrement=True)
    product_code     = Column(String(30), nullable=False, unique=True)
    product_name     = Column(String(100), nullable=False)
    product_category = Column(String(50), nullable=False)
    revenue_model    = Column(String(50), nullable=False)
    fee_rate         = Column(Numeric(6, 4))
    monthly_fee_gbp  = Column(Numeric(8, 2))
    launch_date      = Column(Date, nullable=False)
    is_premium_only  = Column(Boolean, nullable=False, default=False)
    is_active        = Column(Boolean, nullable=False, default=True)
    description      = Column(Text)


class DimCustomer(Base):
    __tablename__ = "dim_customer"
    __table_args__ = {"schema": "warehouse"}

    customer_id             = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_uuid           = Column(UUID(as_uuid=True), nullable=False, unique=True)
    signup_date             = Column(Date, nullable=False)
    signup_date_key         = Column(Integer, ForeignKey("warehouse.dim_date.date_key"), nullable=False)
    country_id              = Column(Integer, ForeignKey("warehouse.dim_country.country_id"), nullable=False)
    channel_id              = Column(Integer, ForeignKey("warehouse.dim_channel.channel_id"), nullable=False)

    age_group               = Column(String(20), nullable=False)
    gender                  = Column(String(20), nullable=False)
    city                    = Column(String(100))
    occupation              = Column(String(50))
    income_band             = Column(String(30))

    kyc_status              = Column(String(20), nullable=False, default="pending")
    kyc_submission_date     = Column(Date)
    kyc_completion_date     = Column(Date)
    activation_date         = Column(Date)
    first_transaction_date  = Column(Date)
    premium_upgrade_date    = Column(Date)
    last_activity_date      = Column(Date)
    churn_date              = Column(Date)

    lifecycle_stage         = Column(String(30), nullable=False, default="registered")
    premium_status          = Column(Boolean, nullable=False, default=False)
    customer_segment        = Column(String(30), nullable=False, default="registered")
    clv_band                = Column(String(20))
    churn_risk_score        = Column(Numeric(5, 2))
    product_count           = Column(SmallInteger, nullable=False, default=0)
    total_revenue_gbp       = Column(Numeric(12, 2), nullable=False, default=0.00)

    device_type             = Column(String(20))
    is_test_customer        = Column(Boolean, nullable=False, default=False)
    created_at              = Column(DateTime, nullable=False, default=datetime.now)
    updated_at              = Column(DateTime, nullable=False, default=datetime.now)

    # Relationships
    country    = relationship("DimCountry")
    channel    = relationship("DimChannel")
    signup_dim = relationship("DimDate")


class FactTransactions(Base):
    __tablename__ = "fact_transactions"
    __table_args__ = {"schema": "warehouse"}

    transaction_id          = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_uuid        = Column(UUID(as_uuid=True), nullable=False)
    customer_id             = Column(BigInteger, ForeignKey("warehouse.dim_customer.customer_id"), nullable=False)
    product_id              = Column(Integer, ForeignKey("warehouse.dim_product.product_id"), nullable=False)
    country_id              = Column(Integer, ForeignKey("warehouse.dim_country.country_id"), nullable=False)
    transaction_date_key    = Column(Integer, ForeignKey("warehouse.dim_date.date_key"), nullable=False)

    transaction_date        = Column(Date, nullable=False)
    transaction_timestamp   = Column(DateTime, nullable=False)
    transaction_type        = Column(String(30), nullable=False)

    amount_local            = Column(Numeric(14, 2), nullable=False)
    currency_code           = Column(String(3), nullable=False)
    currency_factor         = Column(Numeric(10, 6), nullable=False, default=1.0)
    amount_gbp              = Column(Numeric(14, 2), nullable=False)
    fee_amount_local        = Column(Numeric(10, 2), nullable=False, default=0.00)
    fee_amount_gbp          = Column(Numeric(10, 2), nullable=False, default=0.00)

    merchant_name           = Column(String(150))
    merchant_category       = Column(String(50))
    status                  = Column(String(20), nullable=False, default="completed")
    failure_reason          = Column(String(100))
    customer_segment        = Column(String(30))
    is_premium_customer     = Column(Boolean, nullable=False, default=False)
    created_at              = Column(DateTime, nullable=False, default=datetime.now)
