# Cyclomatic Complexity Report
## Scale: 1-10 (1=Simple, 2-4=Low, 5-7=Moderate, 8-10=High)

## Lambda Functions

### lambdas/fixServerRole/index.py
- `check_authorization()` - **3/10** (Low) - Line 133
- `_extract_token()` - **2/10** (Low) - Line 170
- `_validate_arguments()` - **3/10** (Low) - Line 178
- `_authenticate_user()` - **2/10** (Low) - Line 190
- `_fix_iam_role()` - **2/10** (Low) - Line 197
- `handler()` - **4/10** (Low) - Line 208
- `__init__()` - **1/10** (Simple) - Line 26
- `manage_iam_profile()` - **6/10** (Moderate) - Line 31
- `disassociate_iam_profile()` - **5/10** (Moderate) - Line 56
- `attach_iam_profile()` - **6/10** (Moderate) - Line 93
- `check_disassociated_status()` - **2/10** (Low) - Line 75
- `check_associated_status()` - **3/10** (Low) - Line 117

### lambdas/calculateMonthlyRuntime/index.py
- `handler()` - **5/10** (Moderate) - Line 18

### lambdas/listServers/index.py
- `create_default_config()` - **1/10** (Simple) - Line 30
- `validate_shutdown_config()` - **8/10** (High) - Line 51
- `apply_minecraft_config()` - **7/10** (Moderate) - Line 80
- `check_missing_minecraft_config()` - **5/10** (Moderate) - Line 108
- `validate_aws_resources()` - **10/10** (High) - Line 120
- `validate_and_configure_instance_config()` - **9/10** (High) - Line 144
- `extract_auth_token()` - **4/10** (Low) - Line 212
- `get_user_instances()` - **3/10** (Low) - Line 224
- `fetch_parallel_data()` - **5/10** (Moderate) - Line 238
- `build_server_response()` - **2/10** (Low) - Line 247
- `handler()` - **5/10** (Moderate) - Line 292

### lambdas/serverActionProcessor/index.py
- `_strip_leading_zeros()` - **10/10** (High) - Line 40
- `_convert_day_of_week()` - **10/10** (High) - Line 68
- `_convert_timezone_to_utc()` - **4/10** (Low) - Line 90
- `_format_schedule_expression()` - **10/10** (High) - Line 113
- `configure_scheduled_shutdown_event()` - **4/10** (Low) - Line 172
- `remove_scheduled_shutdown_event()` - **3/10** (Low) - Line 228
- `configure_start_event()` - **4/10** (Low) - Line 248
- `remove_start_event()` - **3/10** (Low) - Line 304
- `send_to_appsync()` - **1/10** (Simple) - Line 324
- `_parse_message()` - **2/10** (Low) - Line 336
- `_validate_message()` - **4/10** (Low) - Line 346
- `_route_action()` - **3/10** (Low) - Line 359
- `_send_status_update()` - **2/10** (Low) - Line 377
- `process_server_action()` - **8/10** (High) - Line 385
- `_get_server_context()` - **3/10** (Low) - Line 428
- `_execute_ec2_action()` - **2/10** (Low) - Line 445
- `_send_notification()` - **2/10** (Low) - Line 460
- `handle_server_action()` - **4/10** (Low) - Line 465
- `_save_config_to_db()` - **2/10** (Low) - Line 494
- `_configure_schedule_shutdown()` - **3/10** (Low) - Line 502
- `_configure_alarm_shutdown()` - **3/10** (Low) - Line 521
- `handle_update_server_config()` - **5/10** (Moderate) - Line 534
- `process_create_server()` - **10/10** (High) - Line 561
- `handle_update_server_name()` - **7/10** (Moderate) - Line 672
- `handler()` - **3/10** (Low) - Line 723

### lambdas/getServerMetrics/index.py
- `handler()` - **3/10** (Low) - Line 9
- `get_metric_data()` - **5/10** (Moderate) - Line 102

### lambdas/ssmCommandProcessor/index.py
- `check_instance_ready()` - **5/10** (Moderate) - Line 14
- `send_ssm_command()` - **9/10** (High) - Line 47
- `handler()` - **7/10** (Moderate) - Line 134

### lambdas/serverAction/index.py
- `check_authorization()` - **6/10** (Moderate) - Line 28
- `send_status_to_appsync()` - **1/10** (Simple) - Line 69
- `_is_valid_cron()` - **4/10** (Low) - Line 89
- `validate_create_server_input()` - **10/10** (High) - Line 110
- `validate_queue_message()` - **10/10** (High) - Line 163
- `send_to_queue()` - **7/10** (Moderate) - Line 204
- `action_process_sync()` - **3/10** (Low) - Line 274
- `handle_get_server_users()` - **2/10** (Low) - Line 288
- `handle_search_user_by_email()` - **3/10** (Low) - Line 299
- `handle_create_server()` - **10/10** (High) - Line 334
- `handle_add_user_to_server()` - **7/10** (Moderate) - Line 423
- `handle_get_server_config()` - **3/10** (Low) - Line 493
- `handle_local_invocation()` - **1/10** (Simple) - Line 524
- `handle_search_user_by_email_operation()` - **2/10** (Low) - Line 528
- `handle_create_server_operation()` - **2/10** (Low) - Line 535
- `route_instance_operation()` - **10/10** (High) - Line 542
- `handler()` - **9/10** (High) - Line 600

### lambdas/getMonthlyCost/index.py
- `getUsageCost()` - **5/10** (Moderate) - Line 26
- `handler()` - **10/10** (High) - Line 83

### lambdas/eventResponse/index.py
- `send_to_appsync()` - **1/10** (Simple) - Line 97
- `schedule_event_response()` - **3/10** (Low) - Line 108
- `get_metrics_data()` - **6/10** (Moderate) - Line 136
- `enable_scheduled_rule()` - **2/10** (Low) - Line 182
- `disable_scheduled_rule()` - **3/10** (Low) - Line 189
- `ensure_server_has_cognito_group()` - **4/10** (Low) - Line 201
- `ensure_server_in_dynamodb()` - **2/10** (Low) - Line 247
- `state_change_response()` - **3/10** (Low) - Line 284
- `queue_bootstrap_server()` - **3/10** (Low) - Line 323
- `handle_instance_state_change()` - **4/10** (Low) - Line 346
- `handle_instance_running()` - **7/10** (Moderate) - Line 367
- `handle_instance_stopped()` - **1/10** (Simple) - Line 387
- `handle_scheduled_event()` - **2/10** (Low) - Line 391
- `handler()` - **4/10** (Low) - Line 399

## Layer Helper Functions

### layers/utilHelper/utilHelper.py
- `__init__()` - **1/10** (Simple) - Line 16
- `capitalize_first_letter()` - **2/10** (Low) - Line 22
- `response()` - **2/10** (Low) - Line 36
- `retry_operation()` - **3/10** (Low) - Line 53
- `is_admin_user()` - **2/10** (Low) - Line 62
- `check_user_authorization()` - **9/10** (High) - Line 77
- `get_ssm_param()` - **3/10** (Low) - Line 113
- `get_ssm_parameters()` - **4/10** (Low) - Line 129
- `put_ssm_param()` - **2/10** (Low) - Line 152
- `retrieve_extension_value()` - **4/10** (Low) - Line 167
- `send_server_notification_email()` - **6/10** (Moderate) - Line 217

### layers/ddbHelper/ddbHelper.py
- `__init__()` - **3/10** (Low) - Line 17
- `_to_decimal()` - **3/10** (Low) - Line 30
- `_safe_float()` - **3/10** (Low) - Line 47
- `_safe_int()` - **3/10** (Low) - Line 67
- `_convert_dynamodb_config_item()` - **1/10** (Simple) - Line 86
- `get_server_config()` - **5/10** (Moderate) - Line 115
- `put_server_config()` - **10/10** (High) - Line 145
- `update_server_config()` - **9/10** (High) - Line 209
- `get_server_info()` - **4/10** (Low) - Line 306
- `update_server_name()` - **5/10** (Moderate) - Line 361
- `put_server_info()` - **5/10** (Moderate) - Line 398

### layers/ssmHelper/ssmHelper.py
- `__init__()` - **1/10** (Simple) - Line 12
- `queue_ssm_command()` - **4/10** (Low) - Line 19
- `queue_bootstrap_command()` - **2/10** (Low) - Line 77
- `queue_shell_script()` - **3/10** (Low) - Line 107

### layers/ec2Helper/ec2Helper.py
- `extract_instance_id()` - **3/10** (Low) - Line 21
- `__init__()` - **1/10** (Simple) - Line 28
- `get_latest_ubuntu_ami()` - **2/10** (Low) - Line 39
- `create_ec2_instance()` - **10/10** (High) - Line 55
- `update_alarm()` - **3/10** (Low) - Line 187
- `remove_alarm()` - **3/10** (Low) - Line 221
- `check_alarm_exists()` - **2/10** (Low) - Line 241
- `check_eventbridge_rules_exist()` - **3/10** (Low) - Line 271
- `get_cached_running_minutes()` - **5/10** (Moderate) - Line 271
- `get_total_hours_running_per_month()` - **10/10** (High) - Line 315
- `extract_state_event_time()` - **8/10** (High) - Line 412
- `list_instances_by_user_group()` - **5/10** (Moderate) - Line 429
- `list_instances_by_app_tag()` - **2/10** (Low) - Line 456
- `list_server_by_id()` - **2/10** (Low) - Line 487
- `list_servers_by_user()` - **1/10** (Simple) - Line 498
- `list_servers_by_state()` - **1/10** (Simple) - Line 507
- `list_servers_by_group()` - **1/10** (Simple) - Line 515
- `list_all_servers()` - **1/10** (Simple) - Line 524
- `paginate_instances()` - **6/10** (Moderate) - Line 532
- `describe_iam_profile()` - **3/10** (Low) - Line 570
- `describe_instance_status()` - **6/10** (Moderate) - Line 598
- `describe_instance_attributes()` - **1/10** (Simple) - Line 621
- `update_instance_name_tag()` - **3/10** (Low) - Line 629

### layers/authHelper/authHelper.py
- `extract_auth_token()` - **4/10** (Low) - Line 19
- `validate_user_token()` - **3/10** (Low) - Line 31
- `__init__()` - **1/10** (Simple) - Line 43
- `is_token_valid()` - **6/10** (Moderate) - Line 49
- `process_token()` - **7/10** (Moderate) - Line 85
- `group_exists()` - **2/10** (Low) - Line 132
- `create_group()` - **2/10** (Low) - Line 132
- `add_user_to_group()` - **2/10** (Low) - Line 147
- `list_users_for_group()` - **10/10** (High) - Line 162
- `find_user_by_email()` - **8/10** (High) - Line 233
- `list_groups_for_user()` - **5/10** (Moderate) - Line 291
