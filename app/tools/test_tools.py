from app.tools.operations import (
    get_incident,
    check_sla,
    get_application
)


print("\n--- INCIDENT ---")

incident = get_incident("INC-1042")
print(incident)


print("\n--- SLA ---")

sla = check_sla("INC-1042")
print(sla)


print("\n--- APPLICATION ---")

application = get_application(1)
print(application)
