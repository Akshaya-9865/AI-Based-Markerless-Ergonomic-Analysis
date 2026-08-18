from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Car Seating Comfort Motion Analysis"
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    MAX_UPLOAD_MB: int = 500

    # Pose thresholds
    MIN_VISIBILITY: float = 0.70
    MAX_MISSING_CONSECUTIVE: int = 3

    # Filters (Hz)
    POS_CUTOFF_HZ: float = 6.0
    VEL_CUTOFF_HZ: float = 10.0
    ACC_CUTOFF_HZ: float = 12.0

    # Validation thresholds
    ACC_NOISE_FLAG_MPS2: float = 50.0
    JERK_DISCOMFORT_MPS3: float = 5.0

settings = Settings()
