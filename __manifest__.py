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
        "mail",
        "portal",
        "website"
    ],
    "external_dependencies": {
        'python': ['logging']
    },
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
        "wizards/rechazo_wizard_views.xml",
        "wizards/subir_diseno_wizard_views.xml",
        
        # Vistas del portal
        "views/portal_templates.xml"
    ],
    "application": True,
    "installable": True,
    "auto_install": False
}
