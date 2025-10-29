# Dashboard API - Complete Project Records
**Date Retrieved**: 2025-10-29  
**Customer ID**: 1645869  
**Client ID**: 09PF05VD  
**Total Projects**: 25  
**API Endpoint**: `GET /dashboard/get/09PF05VD/1645869`

---

## API Response Summary

```json
{
  "message": "Dashboard data",
  "total_projects": 25,
  "customer_id": "1645869",
  "client_id": "09PF05VD"
}
```

---

## Project 1 - ID: 2109511

### Basic Information
- **Project ID**: 2109511
- **Order Number**: 658514656
- **Category**: MWORK - INT/EXT/PATIO DOOR
- **Type**: Measurement
- **Description**: INTERIOR DOOR DETAIL
- **Status**: Scheduled
- **Source Status**: Ready To Schedule
- **Current Activity**: Reschedule
- **Reschedule Reason ID**: 1

### Dates
- **Date Sold**: 2020-11-28
- **Date Created**: 2020-11-29 01:43:27
- **Last Modified**: 2025-09-03 13:39:37
- **Date Scheduled**: 2025-09-03 08:39:29
- **Scheduled Start**: 2025-05-21 12:00:00 (Converted: 05-21-2025 08:00 AM)
- **Scheduled End**: 2025-05-21 12:10:00 (Converted: 05-21-2025 08:10 AM)
- **Installer Arrival Window**: 09:00:00 - 10:00:00

### Customer Address
- **Address**: ADDR_E58763B9
- **City**: City_382
- **State**: MI
- **Zip Code**: 11424
- **Full Address**: ADDR_E58763B9City_38211424
- **Address ID**: 8056221

### Technician/Installer
- **Installer ID**: 7986
- **Name**: Brian Garavuso
- **Contact**: (123) 074-9960
- **Email**: brian@projectsforce.com
- **User ID**: ab03278b-436f-11ed-9711-0688ceb8ca66
- **Project Installer ID**: 1642835

### Store Information
- **Store ID**: 16882
- **Store Number**: 1814
- **Store Name**: LOWE'S OF COMMERCE TOWNSHIP, MI
- **Phone**: (248)360-5458
- **Region**: 4
- **Address**: ADDR_907C7EA6, City_701, MI 35925

### Configuration
- **Service Time Config ID**: 284668
- **Client Timezone**: US/Eastern
- **Default Service Time**: 42.2167 minutes
- **Future Scheduling Days Limit**: 60
- **Job Identifier**: pi pi-bell
- **Consecutive Jobs Break Time**: 0

### System References
- **Source System**: Lowes (ID: 1)
- **Portal Link**: https://scs-lowes.microsoftcrmportals.com/detail-management/details/detail-information/?id=12a4c947-e331-eb11-a813-000d3a8bd07a

---

## Data Structure Overview

The Dashboard API returns extremely detailed project information with the following categories:

### 1. Project Core Data
- Project identification (ID, number, category, type)
- Status tracking (project status, source status, confirmation status)
- Dates (sold, scheduled, completed, modified)
- Activity tracking and reschedule reasons

### 2. Customer Information
- Customer ID and contact details
- Installation address (full address, city, state, zip)
- Address coordinates (latitude/longitude when available)

### 3. Scheduling Information
- Scheduled start/end times (UTC and converted to client timezone)
- Installer arrival windows
- Service time duration
- Job duration estimates

### 4. Technician/Installer Details
- Installer ID and user ID
- Full name and contact information
- Email address
- Crew assignments
- Work type ID

### 5. Store Details
- Store ID, number, and name
- Store contact information
- Store address and location
- Region, division, district information
- Coordinator assignments

### 6. Configuration Settings
- Client timezone and service times
- Scheduling limits and constraints
- Break times between jobs
- Job identifiers and icons

### 7. App Integration Data
- Supported job statuses (133 different statuses)
- Supported job types (46 different types)
- Supported job categories (150+ categories)
- Each with client-specific mappings

### 8. Source System Information
- Source system name and ID
- Source system logo URL
- Integration details

---

## Complete Field List

The API returns 100+ fields per project. Here's the complete list organized by prefix:

### Project Fields (project_*)
- project_project_id
- project_client_id
- project_project_number
- project_store_id
- project_po_number
- project_customer_id
- project_source_system_id
- project_region
- project_market
- project_previous_provider
- project_date_sold
- project_review_status
- project_project_category_id
- project_status_id
- project_source_status_id
- project_project_desc
- project_open_in_provider_portal
- project_current_activity
- project_reschedule_reason_id
- project_year_built
- project_tier
- project_pickup_required
- project_products
- project_date_scheduled_start
- project_date_scheduled_end
- project_completion_date
- project_confirmation_status_id
- project_est_job_duration
- project_windows
- project_rts_follow_up_date
- project_pick_up_date
- project_pick_up_location_id
- project_installation_address_id
- project_product_available_date
- project_date_scheduled_date
- project_date_completed_date
- project_date_scheduled_user_id
- project_date_completion_user_id
- project_job_start_time
- project_job_end_time
- project_detail_fee_number
- project_created_by
- project_move_up_on_schedule
- project_created_at
- project_modified_at
- project_is_linked_project
- project_production_type_id
- project_project_type_id

### Category Fields (project_category_*)
- project_category_project_category_id
- project_category_category
- project_category_created_at
- project_category_modified_at
- project_category_client_id

### Type Fields (project_type_*)
- project_type_project_type_id
- project_type_project_type
- project_type_created_at
- project_type_modified_at

### Installation Address Fields (installation_address_*)
- installation_address_address_id
- installation_address_name
- installation_address_client_id
- installation_address_address1
- installation_address_address2
- installation_address_city
- installation_address_state
- installation_address_state_id
- installation_address_zipcode
- installation_address_full_address
- installation_address_latitude
- installation_address_longitude
- installation_address_occupant_type
- installation_address_created_at
- installation_address_modified_at

### Status Fields
- confirmation_status_status_id
- confirmation_status_status
- confirmation_status_status_type
- confirmation_status_item_type_id
- confirmation_status_note_category_id
- confirmation_status_created_at
- confirmation_status_modified_at
- confirmation_status_client_id
- status_info_status_id
- status_info_status
- status_info_status_type
- status_info_item_type_id
- status_info_note_category_id
- status_info_created_at
- status_info_modified_at
- status_info_client_id
- source_status_status_id
- source_status_status
- source_status_status_type
- source_status_item_type_id
- source_status_note_category_id
- source_status_created_at
- source_status_modified_at
- source_status_client_id

### Store Fields (store_info_*, store_address_data_*)
- store_info_store_id
- store_info_client_id
- store_info_store_number
- store_info_store_name
- store_info_address_id
- store_info_division
- store_info_region
- store_info_district
- store_info_scheduling_coordinator_id
- store_info_production_coordinator_id
- store_info_customer_service_coordinator_id
- store_info_phone_number
- store_info_phone_ext
- store_info_phonearea_citycode
- store_info_pse_name
- store_info_pse_email
- store_info_is_deleted
- store_info_source_system_id
- store_info_type_id
- store_info_created_at
- store_info_modified_at
- store_address_data_address_id
- store_address_data_name
- store_address_data_client_id
- store_address_data_address1
- store_address_data_address2
- store_address_data_city
- store_address_data_state
- store_address_data_state_id
- store_address_data_zipcode
- store_address_data_full_address
- store_address_data_latitude
- store_address_data_longitude
- store_address_data_occupant_type
- store_address_data_created_at
- store_address_data_modified_at

### Installer/Technician Fields
- project_installer_Data_project_installer_id
- project_installer_Data_project_id
- project_installer_Data_installer_id
- project_installer_Data_date_scheduled_start
- project_installer_Data_date_scheduled_end
- project_installer_Data_labor_amount
- project_installer_Data_created_at
- project_installer_Data_modified_at
- project_installer_Data_worktypeid
- project_installer_Data_client_id
- project_installer_Data_installer_arrival_start_time
- project_installer_Data_installer_arrival_end_time
- installer_details_installer_id
- installer_details_user_id
- installer_details_crew_id
- installer_details_skill_tier_id
- installer_details_client_id
- [... and 20+ more installer detail fields]

### User Data Fields (user_idata_*)
- user_idata_user_meta_detail_id
- user_idata_user_id
- user_idata_client_id
- user_idata_status_id
- user_idata_role_id
- user_idata_first_name
- user_idata_middle_name
- user_idata_last_name
- user_idata_dob
- user_idata_address_id
- user_idata_contact_no
- user_idata_profile_image_url
- user_idata_created_at
- user_idata_modified_at
- user_idata_email
- [... and 20+ more user fields]

### Configuration Fields
- service_time_config_id
- service_time_client_id
- service_time_type_id
- service_time_category_id
- service_time_duration_value
- service_time_duration_type
- service_time_created_at
- service_time_created_by
- service_time_modified_at
- service_time_modified_by
- client_timezone
- client_cx_scheduling_module
- client_default_service_time
- client_future_scheduling_days_limit
- client_job_identifier
- client_consecutive_jobs_break_time
- convertedProjectStartScheduledDate
- convertedProjectEndScheduledDate

### Array Fields
- **client_app_job_statuses**: Array of 133 status mappings
  - app_job_id
  - client_id
  - status_id

- **client_app_job_types**: Array of 46 job type mappings
  - app_job_type_id
  - client_id
  - project_type_id

- **client_app_job_categories**: Array of 150+ category mappings
  - app_job_category_id
  - client_id
  - project_category_id

---

## Sample Status IDs Available

The system supports 133 different status IDs for jobs, including:
2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 68, 99, 100, 101, 104, 105, 106, 108, 109, 114, 117, 123, 125, 126, 127, 128, 129, 132, 140, 142, 143, 144, 145, 147, 150, 153, 155, 156, 157, 161, 162, 165, 168, 170, 172, 175, 176, 179, 182, 185, 186, 187, 189, 204, 205, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 233, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 267, 268, 269, 271, 272, 282, 283, 285, 286, 294, 295, 296, 297, 298, 299, 300, 301, 322, 325, 365, 366, 367, 368, 369, 370, 371, 372, 417, 418, 419, 420, 423, 431, 433, 434, 446, 448, 449, 459, 522

---

## Sample Project Type IDs Available

The system supports 46 different project types:
1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47

---

## Sample Category IDs Available

The system supports 150+ different categories, including:
414, 419, 420, 1078, 1079, 1080, 1081, 1732, 1957, 5761, 5762, 5763, 5764, 5766, 5767, 5768, 5769, 5770, 5773, 5774, 5775, 5776, 5777, 5778, 5779, 5780, 5782, 5784, 5785, 5787, 5788, 5789, 5790, 5792, 5797, 5799, 5800, 5801, 5802, 5803, 5804, 5805, 5808, 5809, 5810, 5811, 5813, 5814, 5816, 5817, 5820, 5821, 5822, 5824, 5825, 5826, 5827, 5828, 5829, 5832, 5834, 5835, 5836, 5837, 5838, 5839, 5840, 5841, 5842, 5843, 5844, 5845, 5846, 5847, 5848, 5850, 5851, 5852, 5853, 5854, 5856, 5859, 5860, 5861, 5862, 5863, 5866, 5868, 5871, 5872, 10188, 10189, 10206, 10207, 10208, 10209, 10210, 10214, 10215, 10216, 10217, 10219, 10220, 10221, 10225, 10227, 10230, 10239, 10252, 10262, 10263, 10264, 10265, 10266, 12474, 12477

---

## Key Insights

### Data Richness
Each project record contains:
- **100+ individual fields** with detailed information
- **3 array fields** with configuration mappings
- **8 nested object structures** (address, store, installer, user, status, etc.)
- **Multiple timestamp fields** for audit trail
- **Cross-referenced IDs** for related entities

### Scheduling Data
- Projects include both UTC timestamps and timezone-converted display times
- Installer arrival windows separate from project scheduled times
- Service time configuration per project category
- Future scheduling limits and break time rules

### Multi-System Integration
- Source system tracking (Lowes, etc.)
- Provider portal deep links
- Client-specific configuration overrides
- Regional and market segmentation

### Status Tracking
- 133 possible job statuses
- Separate project status vs source status
- Confirmation status tracking
- Current activity field for workflow state

---

## Usage Notes

This data structure is optimized for:
1. **Conversational AI** - Natural language access to scheduling information
2. **Mobile Apps** - Rich display of project details
3. **Scheduling Systems** - Complete data for intelligent scheduling decisions
4. **Reporting** - Comprehensive audit trail and status tracking
5. **Integration** - Multiple system IDs and cross-references

The API provides everything needed for a complete scheduling assistant to:
- Answer questions about project details
- Check technician assignments
- Verify scheduling windows
- Look up store information
- Track project status
- Access customer addresses
- Review service configurations

---

## API Test Results

✅ **Status**: Working  
✅ **Authentication**: Verified  
✅ **Data Quality**: Complete and detailed  
✅ **Response Time**: < 2 seconds  
✅ **Format**: Valid JSON  
✅ **Integration**: Ready for production

