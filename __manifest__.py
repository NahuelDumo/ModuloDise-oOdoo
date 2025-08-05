{
    "name": "Módulo de Diseños",
    "version": "1.0",
    "category": "Project",
    "summary": "Gestión de diseños con listas de verificación por etapas y validación",
    "author": "Nahuel Dumo",
    "license": "AGPL-3",
    "depends": [
        "base",
        "project",
        "mail"
    ],
    "data": [
        # Seguridad
        "security/security.xml",
        "security/ir.model.access.csv",

        # Datos iniciales
        "data/email_templates.xml",

        # Vistas principales
        "views/menu.xml",
        "views/design_views.xml",
        "views/checklist_template_views.xml",
        "views/checklist_item_views.xml",
        "views/revision_log_views.xml",
        
        # Vistas de wizards
        "wizards/rechazo_wizard_views.xml"
    ],
    "application": True,
    "installable": True,
    "auto_install": False
}
