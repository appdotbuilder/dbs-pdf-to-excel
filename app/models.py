from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum


class JobStatus(str, Enum):
    """Status enumeration for PDF processing jobs"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileFormat(str, Enum):
    """Supported file formats for export"""

    EXCEL = "excel"
    CSV = "csv"


# Persistent models (stored in database)
class UploadedFile(SQLModel, table=True):
    """Model for tracking uploaded PDF files"""

    __tablename__ = "uploaded_files"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255, description="Original filename of uploaded PDF")
    file_path: str = Field(max_length=500, description="Server path to stored file")
    file_size: int = Field(description="File size in bytes")
    content_type: str = Field(max_length=100, description="MIME type of uploaded file")
    upload_date: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to extraction jobs
    extraction_jobs: List["ExtractionJob"] = Relationship(back_populates="uploaded_file")


class ExtractionJob(SQLModel, table=True):
    """Model for tracking PDF extraction jobs"""

    __tablename__ = "extraction_jobs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    uploaded_file_id: int = Field(foreign_key="uploaded_files.id")
    status: JobStatus = Field(default=JobStatus.PENDING)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None, max_length=1000)

    # Metadata about extraction process
    total_transactions_found: int = Field(default=0)
    extraction_metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    uploaded_file: UploadedFile = Relationship(back_populates="extraction_jobs")
    transactions: List["Transaction"] = Relationship(back_populates="extraction_job")


class Transaction(SQLModel, table=True):
    """Model for individual credit card transactions extracted from PDF"""

    __tablename__ = "transactions"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    extraction_job_id: int = Field(foreign_key="extraction_jobs.id")

    # Core transaction data
    transaction_date: date = Field(description="Date when transaction occurred")
    billing_date: Optional[date] = Field(default=None, description="Date when transaction was billed")
    description: str = Field(max_length=500, description="Transaction description")
    amount: Decimal = Field(max_digits=10, decimal_places=2, description="Transaction amount")

    # Additional metadata
    raw_text: Optional[str] = Field(default=None, max_length=1000, description="Original raw text from PDF")
    page_number: Optional[int] = Field(default=None, description="PDF page number where transaction was found")
    line_number: Optional[int] = Field(default=None, description="Line number on the page")

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    extraction_job: ExtractionJob = Relationship(back_populates="transactions")


class ExportRecord(SQLModel, table=True):
    """Model for tracking file exports"""

    __tablename__ = "export_records"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    extraction_job_id: int = Field(foreign_key="extraction_jobs.id")
    format: FileFormat = Field(description="Export format")
    filename: str = Field(max_length=255, description="Generated export filename")
    file_path: str = Field(max_length=500, description="Server path to export file")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    download_count: int = Field(default=0, description="Number of times file was downloaded")


# Non-persistent schemas (for validation, forms, API requests/responses)
class FileUploadResponse(SQLModel, table=False):
    """Response schema for file upload"""

    file_id: int
    filename: str
    file_size: int
    upload_date: str  # ISO format datetime string
    message: str


class TransactionCreate(SQLModel, table=False):
    """Schema for creating a new transaction"""

    extraction_job_id: int
    transaction_date: date
    billing_date: Optional[date] = None
    description: str = Field(max_length=500)
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    raw_text: Optional[str] = Field(default=None, max_length=1000)
    page_number: Optional[int] = None
    line_number: Optional[int] = None


class TransactionUpdate(SQLModel, table=False):
    """Schema for updating transaction data"""

    transaction_date: Optional[date] = None
    billing_date: Optional[date] = None
    description: Optional[str] = Field(default=None, max_length=500)
    amount: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)


class TransactionResponse(SQLModel, table=False):
    """Response schema for transaction data"""

    id: int
    transaction_date: str  # ISO format date string
    billing_date: Optional[str] = None  # ISO format date string
    description: str
    amount: str  # String representation of Decimal
    page_number: Optional[int] = None
    line_number: Optional[int] = None
    created_at: str  # ISO format datetime string


class ExtractionJobCreate(SQLModel, table=False):
    """Schema for creating extraction job"""

    uploaded_file_id: int


class ExtractionJobResponse(SQLModel, table=False):
    """Response schema for extraction job"""

    id: int
    uploaded_file_id: int
    status: JobStatus
    started_at: Optional[str] = None  # ISO format datetime string
    completed_at: Optional[str] = None  # ISO format datetime string
    error_message: Optional[str] = None
    total_transactions_found: int
    filename: str  # From related uploaded file


class ExtractionSummary(SQLModel, table=False):
    """Summary schema for extraction results"""

    job_id: int
    filename: str
    status: JobStatus
    total_transactions: int
    date_range: Optional[Dict[str, str]] = None  # {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    total_amount: Optional[str] = None  # String representation of Decimal
    processing_time: Optional[float] = None  # Processing time in seconds


class ExportRequest(SQLModel, table=False):
    """Schema for export requests"""

    extraction_job_id: int
    format: FileFormat = FileFormat.EXCEL
    include_metadata: bool = Field(default=False)


class ExportResponse(SQLModel, table=False):
    """Response schema for export operations"""

    export_id: int
    filename: str
    format: FileFormat
    created_at: str  # ISO format datetime string
    download_url: str


class TransactionFilter(SQLModel, table=False):
    """Schema for filtering transactions"""

    extraction_job_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    description_contains: Optional[str] = None
    page_number: Optional[int] = None


class ProcessingStatistics(SQLModel, table=False):
    """Schema for processing statistics"""

    total_files_uploaded: int
    total_jobs_completed: int
    total_transactions_extracted: int
    average_processing_time: Optional[float] = None
    success_rate: float  # Percentage of successful extractions
