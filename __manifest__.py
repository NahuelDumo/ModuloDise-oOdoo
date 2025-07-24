# modulo_diseno/__manifest__.py
{
    "name": "Modulo de Diseño",
    "version": "1.0",
    "category": "Project",
    "summary": "Gestión de listas de verificación para diseños con validación y etapas",
    "author": "Nahuel Dumo",
    "license": "AGPL-3",
    "depends": ["base", "project", "mail", "portal"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/design_views.xml",
        "views/menu.xml",
        "views/checklist_template_views.xml",
        "views/checklist_item_views.xml",
        "views/revision_log_views.xml",
        "views/wizard_views.xml"
    ],
    "application": True,
    "installable": True,
    "auto_install": False
}
