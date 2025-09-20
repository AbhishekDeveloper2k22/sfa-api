from fastapi import APIRouter, Request, UploadFile, File, Form, Path, Depends, HTTPException, status
import os
from uuid import uuid4
from field_squad.services.employee_service import EmployeeService  
from field_squad.utils.auth import get_current_user
from field_squad.utils.response import format_response, convert_objectid_to_str
import datetime
from typing import List, Optional
from fastapi.responses import StreamingResponse
import io
import traceback

UPLOAD_DIR = "uploads"

def save_upload_file(upload_file: UploadFile, unique_name: str):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())
    return file_path

router = APIRouter()

@router.post("/basic-info")
async def basic_details(request: Request, current_user: dict = Depends(get_current_user)):
    request_json = await request.json()
    
    # Check if this is an edit operation
    is_edit = request_json.get("edit", False)
    employee_id = request_json.get("employeeId")
    
    if is_edit:
        # EDIT OPERATION
        if not employee_id:
            return format_response(
                success=False,
                msg="EmployeeId is required for edit operation",
                statuscode=400,
                data={
                    "employeeId": None,
                    "message": "EmployeeId is required for edit operation"
                }
            )
        
        # Map camelCase to DB field names (snake_case) for edit
        update_user = {
            "full_name": request_json.get("fullName"),
            "email": request_json.get("officialEmail"),
            "personal_email": request_json.get("personalEmail"),
            "mobile_no": request_json.get("mobileNumber"),
            "whatsapp_number": request_json.get("whatsappNumber"),
            "gender": request_json.get("gender"),
            "date_of_birth": request_json.get("dateOfBirth"),
            "blood_group": request_json.get("bloodGroup"),
            "marital_status": request_json.get("maritalStatus"),
            "updated_by": request_json.get("created_by"),
            "date_updated": datetime.datetime.utcnow().isoformat()
        }
        
        # Remove None values to avoid overwriting with None
        update_user = {k: v for k, v in update_user.items() if v is not None}
        
        # Create step0 data for edit (same concept as create)
        step0_data = update_user.copy()
        step0_data.pop("updated_by", None)  # Remove updated_by from step0
        step0_data.pop("date_updated", None)  # Remove date_updated from step0
        
        # Add step0 to the update data
        update_user["step0"] = step0_data
        
        instanceClass = EmployeeService()
        try:
            # Add employee_id to the update data
            update_data = {"_id": employee_id, **update_user}
            result = instanceClass.update_user_data(update_data)
            
            if result.get("success"):
                return format_response(
                    success=True,
                    msg="Basic info updated successfully",
                    statuscode=200,
                    data={
                        "employeeId": employee_id,
                        "message": "Basic info updated successfully"
                    }
                )
            else:
                # Handle duplicate case
                if "User with this" in result.get("msg", "") and "already exists" in result.get("msg", ""):
                    from app.utils.response import extract_steps_from_user_data
                    return format_response(
                        success=False,
                        msg=result.get("msg"),
                        statuscode=400,
                        data={
                            "employeeId": result.get("user_id"),
                            "user_data": extract_steps_from_user_data(convert_objectid_to_str(result.get("user_data"))),
                            "message": result.get("msg")
                        }
                    )
                else:
                    return format_response(
                        success=False,
                        msg=result.get("msg", "Failed to update basic info"),
                        statuscode=404,
                        data={
                            "employeeId": employee_id,
                            "message": result.get("msg", "Failed to update basic info")
                        }
                    )
        except Exception as e:
            return format_response(
                success=False,
                msg=str(e),
                statuscode=500,
                data={
                    "employeeId": employee_id,
                    "message": str(e)
                }
            )
    
    else:
        # CREATE OPERATION (original logic)
        # Map camelCase to DB field names (snake_case)
        insert_user = {
            "full_name": request_json.get("fullName"),
            "email": request_json.get("officialEmail"),
            "personal_email": request_json.get("personalEmail"),
            "mobile_no": request_json.get("mobileNumber"),
            "whatsapp_number": request_json.get("whatsappNumber"),
            "gender": request_json.get("gender"),
            "date_of_birth": request_json.get("dateOfBirth"),
            "blood_group": request_json.get("bloodGroup"),
            "marital_status": request_json.get("maritalStatus"),
            "date_created": datetime.datetime.utcnow().isoformat(),
            "created_by": request_json.get("created_by"),
        }
        db_user = insert_user.copy()
        db_user["step0"] = insert_user

        instanceClass = EmployeeService()
        try:
            result = instanceClass.validate_and_insert_user(db_user)
            # Custom response formatting inside format_response
            if result.get("success"):
                return format_response(
                    success=True,
                    msg="Basic info saved successfully",
                    statuscode=201,
                    data={
                        "employeeId": result.get("user_id"),
                        "message": "Basic info saved successfully"
                    }
                )
            else:
                from app.utils.response import extract_steps_from_user_data
                return format_response(
                    success=False,
                    msg=result.get("msg"),
                    statuscode=400,
                    data={
                        "employeeId": result.get("user_id"),
                        "user_data": extract_steps_from_user_data(convert_objectid_to_str(result.get("user_data"))),
                        "message": result.get("msg")
                    }
                )
        except Exception as e:
            return format_response(
                success=False,
                msg=str(e),
                statuscode=500,
                data={
                    "employeeId": None,
                    "message": str(e)
                }
            )

@router.post("/job-details")
async def job_details(request: Request):
    try:
        request_json = await request.json()
        employee_id = request_json.get("employeeId")
        job_details = {
            "department": request_json.get("department"),
            "designation": request_json.get("designation"),
            "employee_type": request_json.get("employeeType"),
            "joining_date": request_json.get("joiningDate"),
            "work_location": request_json.get("workLocation"),
            "reporting_manager": request_json.get("reportingManager"),
            "employment_status": request_json.get("employmentStatus")
        }
        # Add step2 key with the same data
        db_job_details = job_details.copy()
        db_job_details["step1"] = job_details
        mandatory_fields = [
            ("employeeId", employee_id),
            ("department", job_details["department"]),
            ("designation", job_details["designation"]),
            ("employeeType", job_details["employee_type"]),
            ("joiningDate", job_details["joining_date"]),
            ("workLocation", job_details["work_location"]),
            ("reportingManager", job_details["reporting_manager"]),
            ("employmentStatus", job_details["employment_status"])
        ]
        missing_fields = [name for name, value in mandatory_fields if not value]
        if missing_fields:
            return format_response(
                success=False,
                msg="All fields are mandatory.",
                statuscode=400,
                data={
                    "message": "All fields are mandatory.",
                    "missing_fields": missing_fields
                }
            )
        instanceClass = EmployeeService()
        updated = instanceClass.update_job_details(employee_id, db_job_details)
        if updated:
            return format_response(
                success=True,
                msg="Job details saved successfully",
                statuscode=200,
                data={"message": "Job details saved successfully"}
            )
        else:
            return format_response(
                success=False,
                msg="Failed to update job details.",
                statuscode=404,
                data={"message": "Failed to update job details."}
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=str(e),
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/compensation")
async def compensation(request: Request):
    try:
        request_json = await request.json()
        employee_id = request_json.get("employeeId")
        create_by = request_json.get("createBy")
        compensation_details = {
            "annual_ctc": request_json.get("annualCtc"),
            "basic_salary_percent": request_json.get("basicSalaryPercent"),
            "hra_percent": request_json.get("hraPercent"),
            "special_allowance": request_json.get("specialAllowance"),
            "conveyance_allowance": request_json.get("conveyanceAllowance"),
            "medical_allowance": request_json.get("medicalAllowance"),
            "performance_bonus": request_json.get("performanceBonus"),
            "joining_bonus": request_json.get("joiningBonus"),
            "other_benefits": request_json.get("otherBenefits"),
            "pf_applicable": request_json.get("pfApplicable"),
            "employee_pf_deduction_monthly": request_json.get("employeePfDeductionMonthly"),
            "employee_pf_deduction_yearly": request_json.get("employeePfDeductionYearly"),
            "employer_epf_monthly": request_json.get("employerEpfMonthly"),
            "employer_epf_yearly": request_json.get("employerEpfYearly"),
            "employer_eps_monthly": request_json.get("employerEpsMonthly"),
            "employer_eps_yearly": request_json.get("employerEpsYearly"),
            "employer_pf_deduction_monthly": request_json.get("employerPfDeductionMonthly"),
            "employer_pf_deduction_yearly": request_json.get("employerPfDeductionYearly"),
            "employee_esi_deduction_monthly": request_json.get("employeeEsiDeductionMonthly"),
            "employee_esi_deduction_yearly": request_json.get("employeeEsiDeductionYearly"),
            "pan_no": request_json.get("panNo"),
            "aadhaar_no": request_json.get("aadhaarNo"),
            "bank_account_no": request_json.get("bankAccountNo"),
            "ifsc_code": request_json.get("ifscCode"),
            "bank_name": request_json.get("bankName"),
            "account_type": request_json.get("accountType"),
            "professional_tax_monthly": request_json.get("professionalTaxMonthly"),
            "professional_tax_yearly": request_json.get("professionalTaxYearly"),
            "tds_monthly": request_json.get("tdsMonthly"),
            "tds_yearly": request_json.get("tdsYearly"),
            "monthly_gross_salary": request_json.get("monthlyGrossSalary"),
            "annual_gross_salary": request_json.get("annualGrossSalary"),
            "net_salary_monthly": request_json.get("netSalaryMonthly"),
            "net_salary_yearly": request_json.get("netSalaryYearly"),
            "updated_by": create_by,
            "date_updated": datetime.datetime.utcnow().isoformat()
        }
        # Add step3 key with the same data
        db_compensation = compensation_details.copy()
        db_compensation["step2"] = compensation_details
        # Check mandatory fields
        mandatory_fields = [
            "annual_ctc", "basic_salary_percent", "hra_percent", "pan_no", "aadhaar_no", "bank_account_no", "ifsc_code", "bank_name"
        ]
        if not employee_id or not create_by or not all(compensation_details.get(f) for f in mandatory_fields):
            return format_response(
                success=False,
                msg="All mandatory fields are required.",
                statuscode=400,
                data={"message": "All mandatory fields are required."}
            )
        instanceClass = EmployeeService()
        updated = instanceClass.update_compensation_info(employee_id, db_compensation)
        if updated:
            return format_response(
                success=True,
                msg="Compensation info saved successfully",
                statuscode=200,
                data={"message": "Compensation info saved successfully"}
            )
        else:
            return format_response(
                success=False,
                msg="Failed to update compensation info.",
                statuscode=404,
                data={"message": "Failed to update compensation info."}
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=str(e),
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/system-access")
async def system_access(request: Request):
    try:
        request_json = await request.json()
        employee_id = request_json.get("employeeId")
        access_details = {
            "official_email_username": request_json.get("officialEmailUsername"),
            "password": request_json.get("password"),
            "role_access_level": request_json.get("roleAccessLevel")
        }
        db_access = access_details.copy()
        db_access["step3"] = access_details
        if not employee_id or not all(access_details.values()):
            return format_response(
                success=False,
                msg="All fields are mandatory.",
                statuscode=400,
                data={"message": "All fields are mandatory."}
            )
        instanceClass = EmployeeService()
        updated = instanceClass.update_system_access(employee_id, db_access)
        if updated:
            return format_response(
                success=True,
                msg="System access info saved successfully",
                statuscode=200,
                data={"message": "System access info saved successfully"}
            )
        else:
            return format_response(
                success=False,
                msg="Failed to update system access info.",
                statuscode=404,
                data={"message": "Failed to update system access info."}
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=str(e),
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/emergency-contact")
async def emergency_contact(request: Request):
    try:
        request_json = await request.json()
        employee_id = request_json.get("employeeId")
        contact_details = {
            "contact_name": request_json.get("contactName"),
            "relationship": request_json.get("relationship"),
            "emergency_mobile": request_json.get("emergencyMobile"),
            "emergency_address": request_json.get("emergencyAddress")
        }
        db_contact = contact_details.copy()
        db_contact["step5"] = contact_details
        if not employee_id or not contact_details["contact_name"] or not contact_details["relationship"] or not contact_details["emergency_mobile"]:
            return format_response(
                success=False,
                msg="All mandatory fields are required.",
                statuscode=400,
                data={"message": "All mandatory fields are required."}
            )
        instanceClass = EmployeeService()
        updated = instanceClass.update_emergency_contact(employee_id, db_contact)
        if updated:
            return format_response(
                success=True,
                msg="Emergency contact saved successfully",
                statuscode=200,
                data={"message": "Emergency contact saved successfully"}
            )
        else:
            return format_response(
                success=False,
                msg="Failed to update emergency contact.",
                statuscode=404,
                data={"message": "Failed to update emergency contact."}
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=str(e),
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/address")
async def address(request: Request):
    try:
        request_json = await request.json()
        employee_id = request_json.get("employeeId")
        address_details = {
            "present_address_line1": request_json.get("presentAddressLine1"),
            "present_address_line2": request_json.get("presentAddressLine2"),
            "present_city": request_json.get("presentCity"),
            "present_state": request_json.get("presentState"),
            "present_pin_code": request_json.get("presentPinCode"),
            "present_country": request_json.get("presentCountry"),
            "permanent_address_line1": request_json.get("permanentAddressLine1"),
            "permanent_address_line2": request_json.get("permanentAddressLine2"),
            "permanent_city": request_json.get("permanentCity"),
            "permanent_state": request_json.get("permanentState"),
            "permanent_pin_code": request_json.get("permanentPinCode"),
            "permanent_country": request_json.get("permanentCountry")
        }
        db_address = address_details.copy()
        db_address["step6"] = address_details
        # Check mandatory fields
        mandatory_fields = [
            "present_address_line1", "present_city", "present_state", "present_pin_code", "present_country",
            "permanent_address_line1", "permanent_city", "permanent_state", "permanent_pin_code", "permanent_country"
        ]
        if not employee_id or not all(address_details.get(f) for f in mandatory_fields):
            return format_response(
                success=False,
                msg="All mandatory fields are required.",
                statuscode=400,
                data={"message": "All mandatory fields are required."}
            )
        instanceClass = EmployeeService()
        updated = instanceClass.update_address(employee_id, db_address)
        if updated:
            return format_response(
                success=True,
                msg="Address saved successfully",
                statuscode=200,
                data={"message": "Address saved successfully"}
            )
        else:
            return format_response(
                success=False,
                msg="Failed to update address.",
                statuscode=404,
                data={"message": "Failed to update address."}
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=str(e),
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/hr-notes")
async def hr_notes(request: Request):
    try:
        request_json = await request.json()
        employee_id = request_json.get("employeeId")
        notes_details = {
            "hr_notes": request_json.get("hrNotes")
        }
        db_notes = notes_details.copy()
        db_notes["step7"] = notes_details
        if not employee_id or not notes_details["hr_notes"]:
            return format_response(
                success=False,
                msg="HR notes are required.",
                statuscode=400,
                data={"message": "HR notes are required."}
            )
        instanceClass = EmployeeService()
        updated = instanceClass.update_hr_notes(employee_id, db_notes)
        if updated:
            return format_response(
                success=True,
                msg="HR notes saved successfully",
                statuscode=200,
                data={"message": "HR notes saved successfully"}
            )
        else:
            return format_response(
                success=False,
                msg="Failed to update HR notes.",
                statuscode=404,
                data={"message": "Failed to update HR notes."}
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=str(e),
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/documents")
async def upload_documents(
    employeeId: str = Form(...),
    resumeCv: UploadFile = File(...),
    panCard: UploadFile = File(...),
    aadhaarCard: UploadFile = File(...),
    offerLetter: UploadFile = File(...),
    bankPassbook: UploadFile = File(...),
    educationalCertificates: Optional[List[UploadFile]] = File(None),
    experienceLetter: Optional[UploadFile] = File(None)
):
    try:
        # Generate unique filenames and save files
        def unique_filename(prefix, file: UploadFile):
            ext = os.path.splitext(file.filename)[1]
            return f"{employeeId}_{prefix}_{uuid4().hex}{ext}"

        document_details = {
            "resume_cv": save_upload_file(resumeCv, unique_filename("resume", resumeCv)),
            "pan_card": save_upload_file(panCard, unique_filename("pancard", panCard)),
            "aadhaar_card": save_upload_file(aadhaarCard, unique_filename("aadhaar", aadhaarCard)),
            "offer_letter": save_upload_file(offerLetter, unique_filename("offer", offerLetter)),
            "bank_passbook": save_upload_file(bankPassbook, unique_filename("bank", bankPassbook)),
            "educational_certificates": [
                save_upload_file(f, unique_filename("edu", f)) for f in educationalCertificates
            ] if educationalCertificates else [],
            "experience_letter": save_upload_file(experienceLetter, unique_filename("exp", experienceLetter)) if experienceLetter else None
        }
        db_document = document_details.copy()
        db_document["step4"] = document_details
        instanceClass = EmployeeService()
        updated = instanceClass.update_documents(employeeId, db_document)
        if updated:
            return format_response(
                success=True,
                msg="Documents uploaded successfully",
                statuscode=200,
                data={"message": "Documents uploaded successfully"}
            )
        else:
            return format_response(
                success=False,
                msg="Failed to upload documents.",
                statuscode=404,
                data={"message": "Failed to upload documents."}
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=str(e),
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/submit")
async def final_submit(request: Request):
    try:
        request_json = await request.json()
        employeeId = request_json.get("employeeId")
        createdBy = request_json.get("createdBy")
        if not employeeId or not createdBy:
            return format_response(
                success=False,
                msg="employeeId and createdBy are required.",
                statuscode=400,
                data={"employeeId": employeeId, "message": "employeeId and createdBy are required."}
            )
        all_fields = {
            "final_submission_status": "completed",
            "final_submitted_by": createdBy,
            "final_submitted_at": datetime.datetime.utcnow().isoformat()
        }
        instanceClass = EmployeeService()
        updated = instanceClass.final_submit(employeeId, all_fields)
        if updated:
            return format_response(
                success=True,
                msg="Employee added successfully",
                statuscode=200,
                data={"employeeId": employeeId, "message": "Employee added successfully"}
            )
        else:
            return format_response(
                success=False,
                msg="Failed to submit employee data.",
                statuscode=404,
                data={"employeeId": employeeId, "message": "Failed to submit employee data."}
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=str(e),
            statuscode=500,
            data={"employeeId": None, "message": str(e)}
        )

# Employee List API
@router.post("/employee-list")
async def employee_lists(request: Request):
    try:
        payload = await request.json()
        page = payload.get("page", 1)
        limit = payload.get("limit", 20)
        status = payload.get("status")
        department = payload.get("department")
        role = payload.get("role")
        location = payload.get("location")
        search = payload.get("search")
        instanceClass = EmployeeService()
        result = instanceClass.list_employees(page, limit, status, department, role, location, search)
        # Include pagination data in the response data
        response_data = result["data"]
        if "total" in result:
            response_data = {
                "employees": result["data"],
                "pagination": {
                    "total": result.get("total", 0),
                    "page": result.get("page", 1),
                    "limit": result.get("limit", 20)
                }
            }
        return format_response(success=result["success"], msg="", statuscode=200, data=response_data)
    except Exception as e:
        print(f"Error: {str(e)}")  # Log the error
        traceback.print_exc()
        return format_response(success=False, msg=str(e), statuscode=500, data=None)

# 2. Get Single Employee Details
@router.get("/employee-detail/{id}")
async def get_employee(id: str):
    instanceClass = EmployeeService()
    result = instanceClass.get_employee_by_id(id)
    return format_response(success=result["success"], msg="", statuscode=200, data=result["data"])


@router.post("/bulk-upload/validate")
async def bulk_upload_validate(
    file: UploadFile = File(...),
    createBy: str = Form(...),
    validateData: bool = Form(True)
):
    try:
        if not file or not createBy:
            return format_response(success=False, msg="File and createBy are required.", statuscode=400, data=None)
        instanceClass = EmployeeService()
        result = instanceClass.validate_bulk_upload(file, createBy, validateData)
        return format_response(success=result["success"], msg=result["message"], statuscode=200 if result["success"] else 400, data=result.get("data"))
    except Exception as e:
        return format_response(success=False, msg=str(e), statuscode=500, data=None)

@router.post("/bulk-upload/import")
async def bulk_upload_import(
    file: UploadFile = File(...),
    createBy: str = Form(...),
    skipDuplicates: bool = Form(True),
    updateExisting: bool = Form(False),
    sendNotifications: bool = Form(True),
    sendWelcomeEmails: bool = Form(False),
    validateData: bool = Form(True)
):
    try:
        if not file or not createBy:
            return format_response(success=False, msg="File and createBy are required.", statuscode=400, data=None)
        instanceClass = EmployeeService()
        result = instanceClass.import_bulk_upload(
            file, createBy, skipDuplicates, updateExisting, sendNotifications, sendWelcomeEmails, validateData
        )
        return format_response(success=result["success"], msg=result["message"], statuscode=200 if result["success"] else 400, data=result.get("data"))
    except Exception as e:
        return format_response(success=False, msg=str(e), statuscode=500, data=None)

@router.get("/bulk-upload/template")
async def bulk_upload_template():
    try:
        instanceClass = EmployeeService()
        csv_content = instanceClass.get_bulk_upload_template()
        return StreamingResponse(io.StringIO(csv_content), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=employee_import_template.csv"})
    except Exception as e:
        return format_response(success=False, msg=str(e), statuscode=500, data=None)


# 3. Employee Stats
@router.get("/stats")
async def employee_stats():
    instanceClass = EmployeeService()
    result = instanceClass.get_employee_stats()
    return format_response(
        success=result["success"], 
        msg="Employee stats retrieved successfully" if result["success"] else "Failed to retrieve employee stats", 
        statuscode=200 if result["success"] else 500, 
        data=result["data"]
    )

# 4. Employee Analytics
@router.get("/analytics")
async def employee_analytics():
    instanceClass = EmployeeService()
    result = instanceClass.get_employee_analytics()
    return format_response(success=result["success"], msg="", statuscode=200, data=result["data"])

# 7. Delete Employee
@router.delete("/{id}")
async def delete_employee(id: str):
    instanceClass = EmployeeService()
    result = instanceClass.delete_employee(id)
    return format_response(success=result["success"], msg=result["message"], statuscode=200)

# 8. Employee Audit Log
@router.get("/audit-log")
async def employee_audit_log(
    employeeId: str = None,
    action: str = None,
    dateFrom: str = None,
    dateTo: str = None
):
    instanceClass = EmployeeService()
    result = instanceClass.get_audit_log(employeeId, action, dateFrom, dateTo)
    return format_response(success=result["success"], msg="", statuscode=200, data=result["data"])

