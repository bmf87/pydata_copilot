import abc
import os
import pandas as pd
from typing import Optional, Any
import streamlit as st


log = st.logger.get_logger(__name__)

class DatasetHandler(abc.ABC):
    """
    Interface/Base class for handling file uploads from Streamlit.
    """
    def __init__(self, max_file_size_bytes: int = 200 * 1024 * 1024):
        """
        Initialize the DatasetHandler with file size constraints.
        
        Args:
            max_file_size_bytes (int): Maximum allowed file size in bytes (default: 200MB)
        """
        self.max_file_size_bytes = max_file_size_bytes
        self.df: Optional[pd.DataFrame] = None
        self.file_size: int = 0
        self.file_name: Optional[str] = None
        self.file_type: Optional[str] = None

    def validate_file_size(self, file_object: Any) -> None:
        """
        Safeguard method that validates if the uploaded file size is within acceptable limitations.
        
        Args:
            file_object: The uploaded file object from Streamlit
            
        Raises:
            ValueError: If the file size exceeds max_file_size_bytes
        """
        if hasattr(file_object, 'size'):
            size = file_object.size
        else:
            # Fallback for file-like objects without a 'size' attribute
            file_object.seek(0, os.SEEK_END)
            size = file_object.tell()
            file_object.seek(0)
            
        if size > self.max_file_size_bytes:
            raise ValueError(
                f"File size {size} bytes exceeds the maximum limit of {self.max_file_size_bytes} bytes."
            )
        self.file_size = size

    def handle_upload(self, file_object: Any) -> pd.DataFrame:
        """
        Main method to handle all file upload activity: validation, loading, and reading.
        
        Args:
            file_object: The Streamlit UploadedFile object.
            
        Returns:
            pd.DataFrame: The loaded dataset.
        """
        self.file_name = getattr(file_object, 'name', 'unknown_file')
        self.file_type = getattr(file_object, 'type', 'unknown_type')
   
        # Safeguards & Size Check
        self.validate_file_size(file_object)
        
        # Read contents into a dataframe
        self.df = self.read_file(file_object)
        self._normalize_columns()
        return self.df

    @abc.abstractmethod
    def read_file(self, file_object: Any) -> pd.DataFrame:
        """
        Abstract method to be implemented by concrete classes for specific file reading (csv, xlsx, parquet).
        """
        pass

    def get_schema(self) -> dict:
        """
        Provide the schema of the data, mapping column names to their data types.
        """
        self._check_data_loaded()
        return self.df.dtypes.astype(str).to_dict()

    def get_columns(self) -> list:
        """
        Provide the list of columns available in the dataset.
        """
        self._check_data_loaded()
        return list(self.df.columns)

    def get_descriptive_statistics(self, include: str = 'all') -> pd.DataFrame:
        """
        Get descriptive statistics on the data (similar to pandas describe).
        """
        self._check_data_loaded()
        try:
            desc = self.df.describe(include=include)
        except ValueError:
            desc = self.df.describe(include='all')
        return desc

    def get_head(self, n: int = 5) -> pd.DataFrame:
        """
        Utility method to get a sample of the head of the data.
        
        Args:
            n (int): Number of rows to return.
        """
        self._check_data_loaded()
        return self.df.head(n)

    def _normalize_columns(self) -> None:
        """
        Normalize column names to be snake_case.
        """
        self._check_data_loaded()
        self.df.columns = (self.df.columns
            .str.strip()
            .str.lower()
            .str.replace(' ', '_')
            .str.replace('[^a-zA-Z0-9_]', '', regex=True) # replace any non-alphanumeric character with an empty string
        )

    def _check_data_loaded(self) -> None:
        """
        Internal utility to ensure data is loaded before analytical / extraction operations.
        """
        if self.df is None:
            raise ValueError("No data is loaded. Please call `handle_upload(file_object)` first.")


class CSVDatasetHandler(DatasetHandler):
    """
    Concrete class for handling CSV file uploads.
    Handles both utf-8 and latin1 encodings.
    """
    def read_file(self, file_object: Any) -> pd.DataFrame:
        # Leverage pandas read_csv
        try:
            df = pd.read_csv(file_object, encoding='utf-8', header=0)
        except UnicodeDecodeError:
            df = pd.read_csv(file_object, encoding='latin1', header=0)
        
        return df


class ExcelDatasetHandler(DatasetHandler):
    """
    Concrete class for handling Excel (XLSX) file uploads.
    """
    def read_file(self, file_object: Any) -> pd.DataFrame:
        # Leverage pandas read_excel
        return pd.read_excel(file_object)


class ParquetDatasetHandler(DatasetHandler):
    """
    Concrete class for handling Parquet file uploads.
    """
    def read_file(self, file_object: Any) -> pd.DataFrame:
        # Leverage pandas read_parquet
        return pd.read_parquet(file_object)


def get_dataset_handler(file_type: str, max_file_size_bytes: int = 10 * 1024 * 1024) -> DatasetHandler:
    """
    Factory utility to instantiate the correct DatasetHandler concrete class 
    based on the file type passed from Streamlit (e.g., uploaded_file.type).
    
    Args:
        file_type (str): The MIME type from Streamlit `uploaded_file.type`.
        max_file_size_bytes (int): Max filesize limitation limit.
        
    Returns:
        DatasetHandler: The appropriate concrete dataset handler instance.
    """
    # Streamlit commonly uses these MIME types for CSVs
    csv_types = ['text/csv', 'application/csv', 'application/x-csv', 'text/comma-separated-values']
    
    # Streamlit commonly uses these MIME types for Excel
    excel_types = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', # .xlsx
        'application/vnd.ms-excel', # .xls
        'application/excel'
    ]
    
    # Parquet MIME types (octet-stream is a common catch-all)
    parquet_types = [
        'application/octet-stream', 
        'application/x-parquet', 
        'application/vnd.apache.parquet',
        'application/parquet'
    ]

    log.debug(f"File type passed into get_dataset_handler: {file_type}")
    
    # Determine the appropriate handler based on the passed file_type
    if file_type in csv_types:
        return CSVDatasetHandler(max_file_size_bytes=max_file_size_bytes)
    elif file_type in excel_types:
        return ExcelDatasetHandler(max_file_size_bytes=max_file_size_bytes)
    elif file_type in parquet_types:
        return ParquetDatasetHandler(max_file_size_bytes=max_file_size_bytes)
    else:
        raise ValueError(f"Unsupported file type for upload: {file_type}")
