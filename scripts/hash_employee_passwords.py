from app.services.employee_service import EmployeeService

if __name__ == "__main__":
    print("Hashing all plain text passwords in employee_master collection...")
    service = EmployeeService()
    service.hash_all_plaintext_passwords()
    print("Done. All plain text passwords have been hashed (if any existed).") 