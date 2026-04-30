import frappe


def execute():
    if not frappe.db.exists("DocType", "CA Company Tax Config"):
        return

    # frappe.reload_doc does not reliably sync child-table permissions on
    # existing installs. Write directly to tabDocPerm instead.
    existing = frappe.db.get_value(
        "DocPerm",
        {
            "parent": "CA Company Tax Config",
            "role": "System Manager",
            "permlevel": 0,
        },
        "name",
    )

    if existing:
        frappe.db.set_value(
            "DocPerm",
            existing,
            {"read": 1, "write": 1, "create": 1, "delete": 1, "email": 1,
             "print": 1, "report": 1, "export": 1, "share": 1},
        )
    else:
        frappe.db.sql(
            """
            INSERT INTO `tabDocPerm`
                (`name`, `creation`, `modified`, `modified_by`, `owner`, `docstatus`,
                 `parent`, `parenttype`, `parentfield`,
                 `role`, `permlevel`,
                 `read`, `write`, `create`, `delete`,
                 `submit`, `cancel`, `amend`,
                 `print`, `email`, `report`, `export`, `share`)
            VALUES
                (%s, NOW(), NOW(), 'Administrator', 'Administrator', 0,
                 'CA Company Tax Config', 'DocType', 'permissions',
                 'System Manager', 0,
                 1, 1, 1, 1, 0, 0, 0,
                 1, 1, 1, 1, 1)
            """,
            (frappe.generate_hash("", 10),),
        )

    frappe.clear_cache(doctype="CA Company Tax Config")
    frappe.db.commit()
