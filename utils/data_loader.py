
from pathlib import Path

import pandas as pd
import streamlit as st


# --------------------------------------------------
# 1. Locate the project data folder
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


# --------------------------------------------------
# 2. Load and prepare the CSV files
# --------------------------------------------------
@st.cache_data
def load_data():
    """
    Load the sales, customers and products datasets.
    Cache the results so Streamlit doesn't reread the
    CSV files unnecessarily on every rerun.
    """

    sales_path = DATA_DIR / "sales.csv"
    customers_path = DATA_DIR / "customers.csv"
    products_path = DATA_DIR / "products.csv"

    # Check that all required files exist
    for file_path in [sales_path, customers_path, products_path]:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Required data file not found: {file_path}"
            )

    # Read the CSV files
    sales = pd.read_csv(sales_path)
    customers = pd.read_csv(customers_path)
    products = pd.read_csv(products_path)

    # Convert dates
    sales["Order_Date"] = pd.to_datetime(
        sales["Order_Date"],
        errors="coerce"
    )

    if "Delivery_Date" in sales.columns:
        sales["Delivery_Date"] = pd.to_datetime(
            sales["Delivery_Date"],
            errors="coerce"
        )

    # Convert numeric columns where available
    numeric_columns = [
        "Quantity",
        "Unit_Price",
        "Order_Value",
        "Shipping_Cost",
        "Coupon_Discount",
        "Total_Amount",
    ]

    for column in numeric_columns:
        if column in sales.columns:
            sales[column] = pd.to_numeric(
                sales[column],
                errors="coerce"
            )

    # Standardize text fields
    for column in ["State", "City", "Order_Status", "Payment_Mode"]:
        if column in sales.columns:
            sales[column] = sales[column].astype("string").str.strip()

    # Add product category to sales without duplicating rows
    if {"Product_ID", "Category"}.issubset(products.columns):
        product_categories = (
            products[["Product_ID", "Category"]]
            .drop_duplicates(subset=["Product_ID"])
            .set_index("Product_ID")["Category"]
        )

        sales["Category"] = sales["Product_ID"].map(product_categories)

    return sales, customers, products
