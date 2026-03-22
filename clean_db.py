import logging

from supabase import create_client, Client

# ==========================================
# 0. Logger Setup
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 1. Configuration (ใส่ URL และ Key ของคุณ)
# ==========================================
# TODO: เปลี่ยนเป็น URL และ KEY ของ Supabase โพรเจกต์คุณ
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"

def clean_database() -> None:
    """
    Connects to Supabase and deletes garbage rows in the 'orders' table.
    Targets rows where 'Order ID' or 'Shipped Time' are null or empty.
    """
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Connected to Supabase successfully.")

        # 1. ลบแถวที่ Order ID เป็นค่าว่าง (NULL)
        res_null_id = supabase.table("orders").delete().is_("Order ID", "null").execute()
        logger.info("Deleted %d rows where 'Order ID' was NULL.", len(res_null_id.data))

        # 2. ลบแถวที่ Order ID เป็นแค่ช่องว่าง ("")
        res_empty_id = supabase.table("orders").delete().eq("Order ID", "").execute()
        logger.info("Deleted %d rows where 'Order ID' was empty.", len(res_empty_id.data))
        
        # 3. ลบแถวที่ Shipped Time เป็นค่าว่าง (NULL) - สำหรับออเดอร์ค้าง/ยกเลิก
        res_null_time = supabase.table("orders").delete().is_("Shipped Time", "null").execute()
        logger.info("Deleted %d rows where 'Shipped Time' was NULL.", len(res_null_time.data))

        # 4. ลบแถวที่ Shipped Time เป็นแค่ช่องว่าง ("")
        res_empty_time = supabase.table("orders").delete().eq("Shipped Time", "").execute()
        logger.info("Deleted %d rows where 'Shipped Time' was empty.", len(res_empty_time.data))

        logger.info("Database cleanup completed successfully!")

    except KeyError as ke:
        logger.error("Configuration error: %s", ke)
    except Exception as e:
        logger.error("An error occurred during cleanup: %s", e)

if __name__ == "__main__":
    clean_database()