import re
from functools import wraps

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
import json
from .forms import RegistrationForm
from .models import UserConfiguration, UserSavedJob


# Users must belong to this group for an admin to grant them access to the app.
# New registrations are not added to it automatically.
ACCESS_GROUP_NAME = "Utilisateurs actifs"


def access_required(view_func):
    """Require login AND membership in ACCESS_GROUP_NAME.

    Logged-in users who haven't been approved by an admin yet see a
    pending-approval page instead of the protected view.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.groups.filter(name=ACCESS_GROUP_NAME).exists():
            return render(request, "auth/pending_approval.html", status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


# Default groups (server-side definitions)
DEFAULT_GROUPS = [
    {"id": 1, "name": "Tarifs adhérent pour les machines", "options": [
        {"name": "Non"},
        {"name": "Oui"}
    ]},
    {"id": 2, "name": "Matière", "options": [
        {"name":"Sans","type":"","epaisseur":"","prix":0,"url_achat":""},
        {"name":"PMMA Plexi 3mm","type":"panneau_laser","epaisseur":3,"prix":45,"url_achat":""},
        {"name":"PMMA Plexi 6mm","type":"panneau_laser","epaisseur":6,"prix":149.5,"url_achat":""},
        {"name":"PMMA Plexi 8mm","type":"panneau_laser","epaisseur":8,"prix":191.07,"url_achat":""},
        {"name":"LaserMaxx 3mm","type":"panneau_laser","epaisseur":3,"prix":105,"url_achat":""},
        {"name":"CP Ordinaire 5mm","type":"panneau_laser","epaisseur":5,"prix":23.9,"url_achat":""},
        {"name":"CP Ordinaire 10mm","type":"panneau_laser","epaisseur":10,"prix":37,"url_achat":""},
        # NOTE: prix 23.9 is identical to "CP Ordinaire 5mm" above; looks like a copy-paste, to be verified.
        {"name":"CP Ordinaire 15mm","type":"panneau_laser","epaisseur":15,"prix":23.9,"url_achat":""},
        {"name":"CP Ordinaire 18mm","type":"panneau_laser","epaisseur":18,"prix":58.9,"url_achat":""},
        {"name":"Bois BALSA 4mm","type":"panneau_laser","epaisseur":4,"prix":145,"url_achat":""},
        {"name":"CP Peuplier 3mm","type":"panneau_laser","epaisseur":3,"prix":12,"url_achat":""},
        {"name":"CP Peuplier 5mm","type":"panneau_laser","epaisseur":5,"prix":12,"url_achat":""},
        {"name":"CP Peuplier 10mm","type":"panneau_laser","epaisseur":10,"prix":16,"url_achat":""},
        {"name":"CP Peuplier 15mm","type":"panneau_laser","epaisseur":15,"prix":20,"url_achat":""},
        {"name":"CP Peuplier 18mm","type":"panneau_laser","epaisseur":18,"prix":120,"url_achat":""},
        {"name":"Carton Bois 0,7mm","type":"panneau_laser","epaisseur":0.7,"prix":2.969,"url_achat":""},
        {"name":"Carton Bois 2mm","type":"panneau_laser","epaisseur":2,"prix":8.333,"url_achat":""},
        {"name":"Carton Bois 3mm","type":"panneau_laser","epaisseur":3,"prix":10.938,"url_achat":""},
        {"name":"MDF 3mm brut","type":"panneau_laser","epaisseur":3,"prix":7.9,"url_achat":""},
        {"name":"MDF 6mm Brut","type":"panneau_laser","epaisseur":6,"prix":13,"url_achat":""},
        {"name":"MDF 10mm Brut","type":"panneau_laser","epaisseur":10,"prix":14.9,"url_achat":""},
        {"name":"MDF 15mm Brut","type":"panneau_laser","epaisseur":15,"prix":18.9,"url_achat":""},
        {"name":"MDF 18mm Brut","type":"panneau_laser","epaisseur":18,"prix":20.9,"url_achat":""},
        {"name":"MDF 22mm Brut","type":"panneau_laser","epaisseur":22,"prix":24.9,"url_achat":""},
        {"name":"PET-G Translucide teint","type":"filament","epaisseur":1.75,"prix":0.03,"url_achat":""},
        {"name":"PET-G Translucide non teint","type":"filament","epaisseur":1.75,"prix":0.03,"url_achat":""},
        {"name":"Filament Souple","type":"filament","epaisseur":1.75,"prix":0.042,"url_achat":""},
        {"name":"Fil Réactif au UV","type":"filament","epaisseur":1.75,"prix":0.036,"url_achat":""},
        {"name":"Filament Acier","type":"filament","epaisseur":1.75,"prix":0.065,"url_achat":""},
        {"name":"Filament Bois","type":"filament","epaisseur":1.75,"prix":0.033,"url_achat":""},
        {"name":"Filament Cuivre","type":"filament","epaisseur":1.75,"prix":0.067,"url_achat":""},
        {"name":"Filament Or","type":"filament","epaisseur":1.75,"prix":0.078,"url_achat":""},
        {"name":"Filament Pierre","type":"filament","epaisseur":1.75,"prix":0.033,"url_achat":""},
        {"name":"Fil Réactif à la chaleur","type":"filament","epaisseur":1.75,"prix":0.036,"url_achat":""},
        {"name":"ABS 1 kg","type":"filament","epaisseur":1.75,"prix":0.022,"url_achat":""},
        {"name":"ICE PLA B2.3Kg","type":"filament","epaisseur":1.75,"prix":0.017,"url_achat":"http://amzn.eu/d/9q8A8dd"},
        {"name":"PLA 1 Kg","type":"filament","epaisseur":1.75,"prix":0.025,"url_achat":""},
        {"name":"PLA Couleur","type":"filament","epaisseur":1.75,"prix":0.025,"url_achat":""},
        {"name":"PLA fuorecent","type":"filament","epaisseur":1.75,"prix":0.025,"url_achat":""},
        {"name":"PLA Marbre","type":"filament","epaisseur":1.75,"prix":0.03,"url_achat":""},
        {"name":"PLA pailleté","type":"filament","epaisseur":1.75,"prix":0.036,"url_achat":""},
        {"name":"PLA Phosphorescent","type":"filament","epaisseur":1.75,"prix":0.028,"url_achat":""},
        {"name":"Résine_Noire","type":"resine","epaisseur":"","prix":0.04,"url_achat":""},
        {"name":"PVC 10 mm","type":"panneau","epaisseur":"","prix":72.07,"url_achat":""}
    ]},
    {"id": 3, "name": "Consommable", "options": [
        {"name":"_Sans","prix":0,"duree_vie_totale_minutes":1},
        {"name":"Alcool_Iso","prix":50,"duree_vie_totale_minutes":2000},
        {"name":"Fraise D3,17 1 dent","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 1 dent aluminium","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 1 dent DLC","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 1 dent EVO","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 1 dent EVOMAX","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 1 dent gauche","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 2 dents droites","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 2 dents EVOMAX","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 2 dents fishtail EVO","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 2 dents gauche fishtail EVO","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 2 dents hémisphérique","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17 3 dents EVO","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17  à graver","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17  coupe diamant","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D3,17  coupe diamant CVD-D","prix":12.9,"duree_vie_totale_minutes":345},
        {"name":"Fraise D3,17  hélicoïdales 2 dents","prix":12.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D4 1 dent DLC","prix":14.9,"duree_vie_totale_minutes":345},
        {"name":"Fraise D4 2 dents droites","prix":14.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D4 2 dents Revêtues","prix":14.9,"duree_vie_totale_minutes":345},
        {"name":"Fraise D6 1 dent","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 1 dent DLC","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 1 dent EVO","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 2 dents Alu","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 2 dents droites","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 2 dents gauche fishtail EVO","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 2 dents hémisphérique","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 2 dents Revêtues","prix":25,"duree_vie_totale_minutes":345},
        {"name":"Fraise D6 3 dents Alu","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 4 dents bois EVO","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 coupe diamant","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 hélicoïdales 2 dents","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D6 helicoïdales 2 dents EVO","prix":21.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D8 2 dents Alu","prix":25.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D8 2 dents droites","prix":25.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D8 3 dents Alu","prix":25.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D8 4 dents bois EVO","prix":25.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D8 hélicoïdales 1 dent","prix":25.9,"duree_vie_totale_minutes":240},
        {"name":"Fraise D8 hélicoïdales 2 dents","prix":25.9,"duree_vie_totale_minutes":240}
    ]},
    {"id": 4, "name": "Logiciel de modélisation", "options": [
        {"name":"Aucun","prix_mensuel":0},
        {"name":"Autocad","prix_mensuel":258},
        {"name":"Fusion 360 Entreprise","prix_mensuel":42},
        {"name":"Fusion 360 Start-Up","prix_mensuel":0},
        {"name":"Rhino 6","prix_mensuel":27.8}
    ]},
    {"id": 5, "name": "Type de prestation", "options": [
        {"name": "One-Shot", "taux_horaire": 40},
        {"name": "> 2", "taux_horaire": 35},
        {"name": " > 10", "taux_horaire": 25},
        {"name": "Modelisation", "taux_horaire": 60},
        {"name": "Coût homme OFFERT", "taux_horaire": 0}
    ]},
    {"id": 6, "name": "Type de licence", "options": [
        {"name":"CC-Zero","description":"Zéro","prix":0},
        {"name":"CC-BY-SA","description":"Attribution - Partage dans les Mêmes Conditions","prix":0},
        {"name":"CC-BY-NC-SA","description":"Attribution - Pas d'utilisation commerciale - Partage dans les Mêmes Conditions","prix":10},
        {"name":"CC-BY-ND-SA","description":"Attribution - Pas de modification - Partage dans les Mêmes Conditions","prix":20},
        {"name":"CC-BY-NC-ND-SA","description":"Attribution - Pas d'utilisation commerciale - Pas de modification - Partage dans les Mêmes Conditions","prix":30},
        {"name":"CC-BY-NC-ND-DP-SA","description":"Attribution - Pas d'utilisation commerciale - Pas de modification - Pas de diffusion - Partage dans les Mêmes Conditions","prix":50}
]},
    {"id": 7, "name": "Majoration pour urgence, déplacements...", "options": [
        {"name": "Aucun", "majoration_coef": 1},
        {"name": "Urgent", "majoration_coef": 1.2},
        {"name": "Travail en soirée", "majoration_coef": 1.9}
    ]},
    {"id": 8, "name": "Contribution au projet asso", "options": [
        {"name": "base", "pourcentage_contribution": 0.1},
        {"name": "Bonus -2", "pourcentage_contribution": 0.15},
        {"name": "Bonus -1", "pourcentage_contribution": 0.2},
        {"name": "Normal", "pourcentage_contribution": 0.3},
        {"name": "Bonus +1", "pourcentage_contribution": 0.5},
        {"name": "Bonus +2", "pourcentage_contribution": 0.8},
        {"name": "Bonus +3", "pourcentage_contribution": 0.9}
    ]},
    {"id": 9, "name": "Machine", "options": [
        {"name": "Sans_Machine","type": "None","prix_achat": "","cout_fonctionnement": "","duree_amortissement_mois": 60,"prix_adherent": 0,"prix_normal": 0,"majoration": 0,"pourcent_temps": ""},
        {"name": "Créality Under3_Pro_V2","type": "imprimante_3D","prix_achat": 300,"cout_fonctionnement": 2.5,"duree_amortissement_mois": 36,"prix_adherent": 3,"prix_normal": 5,"majoration": 5,"pourcent_temps": 15},
        {"name": "Ultimaker S5","type": "imprimante_3D","prix_achat": 6500,"cout_fonctionnement": 3,"duree_amortissement_mois": 60,"prix_adherent": 5,"prix_normal": 8,"majoration": 3,"pourcent_temps": 15},
        {"name": "CNC 2300*1300","type": "cnc","prix_achat": 15000,"cout_fonctionnement": 10,"duree_amortissement_mois": 60,"prix_adherent": 13,"prix_normal": 20,"majoration": 13,"pourcent_temps": 30},
        {"name": "Découpe Vinyle","type": "vinyl_cutter","prix_achat": 500,"cout_fonctionnement": 2.5,"duree_amortissement_mois": 36,"prix_adherent": 3,"prix_normal": 5,"majoration": 10,"pourcent_temps": 30},
        {"name": "Résine Mono X","type": "imprimante_3D_resine","prix_achat": 1500,"cout_fonctionnement": 5,"duree_amortissement_mois": 60,"prix_adherent": 6,"prix_normal": 9,"majoration": 5,"pourcent_temps": 20},
        {"name": "Mini Découpe Laser","type": "laser_cutter","prix_achat": 500,"cout_fonctionnement": 2.5,"duree_amortissement_mois": 36,"prix_adherent": 3,"prix_normal": 5,"majoration": 5,"pourcent_temps": 15},
        {"name": "Mini CNC 3018","type": "cnc","prix_achat": 500,"cout_fonctionnement": 2.5,"duree_amortissement_mois": 36,"prix_adherent": 3,"prix_normal": 5,"majoration": 5,"pourcent_temps": 10},
        {"name": "CNC ALU 3040","type": "cnc","prix_achat": 7500,"cout_fonctionnement": 13,"duree_amortissement_mois": 60,"prix_adherent": 15,"prix_normal": 23,"majoration": 13,"pourcent_temps": 30},
        {"name": "Découpe Laser","type": "laser_cutter","prix_achat": 20000,"cout_fonctionnement": 5,"duree_amortissement_mois": 100,"prix_adherent": 7,"prix_normal": 11,"majoration": 10,"pourcent_temps": 20},
        {"name": "FLSUN-V400","type": "imprimante_3D","prix_achat": 800,"cout_fonctionnement": 5,"duree_amortissement_mois": 12,"prix_adherent": 6,"prix_normal": 9,"majoration": 3,"pourcent_temps": 15},
        {"name": "CNC ALPHA XL","type": "cnc","prix_achat": 12000,"cout_fonctionnement": 10,"duree_amortissement_mois": 60,"prix_adherent": 12,"prix_normal": 18,"majoration": 13,"pourcent_temps": 30}
    ]},
]

# Property keys (besides "name") that ship with each group's default options.
# The cost formulas in app.js depend on these, so the options modal must not
# let users delete them - only user-added properties are removable there.
for _group in DEFAULT_GROUPS:
    _group["default_keys"] = sorted({
        key for option in _group["options"] for key in option.keys() if key != "name"
    })
del _group


MAX_CONFIGURATIONS_BODY_BYTES = 256 * 1024
MAX_OPTIONS_PER_GROUP = 200
MAX_SAVED_JOB_STATE_BYTES = 256 * 1024
MAX_SAVED_JOBS_PER_USER = 200

KNOWN_GROUP_IDS = {g["id"] for g in DEFAULT_GROUPS}

# Option property keys end up as data-<key> attribute names in templates and as
# el.dataset[key] in JS; anything beyond letters/digits/_/- (e.g. spaces or
# quotes) could break out of the attribute and inject arbitrary markup.
PROPERTY_KEY_RE = re.compile(r"[\w-]+")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("abaque:index")
        else:
            return render(request, "auth/login.html", {"error": "Identifiants invalides"})

    return render(request, "auth/login.html")


# POST-only: logging someone out via a crafted GET link is a CSRF vector
# (Django's own LogoutView dropped GET support in 5.0 for the same reason).
@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect("login")


def register_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("abaque:index")
    else:
        form = RegistrationForm()

    return render(request, "auth/register.html", {"form": form})


@access_required
def index(request):
    """Main app page with groups"""
    user_configs = {
        config.group_id: config.options_json
        for config in UserConfiguration.objects.filter(user=request.user)
    }

    groups = []
    for g in DEFAULT_GROUPS:
        group_copy = g.copy()
        # Get user's customized options if they exist, otherwise use defaults
        group_copy["options"] = user_configs.get(g["id"], g["options"])
        groups.append(group_copy)

    return render(request, "abaque/index.html", {"groups": groups})


def _validate_configurations_payload(data):
    """Validate the configurations POST body. Returns an error message, or None if valid."""
    if not isinstance(data, dict):
        return "Invalid payload: expected an object"

    for group_id, options in data.items():
        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            return "Invalid payload: group id must be an integer"

        if group_id not in KNOWN_GROUP_IDS:
            return "Invalid payload: unknown group id"

        if not isinstance(options, list):
            return "Invalid payload: options must be a list"

        if len(options) > MAX_OPTIONS_PER_GROUP:
            return "Invalid payload: too many options for a group"

        for option in options:
            if not isinstance(option, dict):
                return "Invalid payload: each option must be an object"
            name = option.get("name")
            if not isinstance(name, str) or not name.strip():
                return "Invalid payload: each option requires a non-empty name"
            for key in option:
                if key != "name" and not PROPERTY_KEY_RE.fullmatch(key):
                    return "Invalid payload: invalid property name"

    return None


@access_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def api_get_configurations(request):
    """Get all user configurations (JSON)"""
    if request.method == "GET":
        configs = UserConfiguration.objects.filter(user=request.user)
        result = {}
        for config in configs:
            result[str(config.group_id)] = config.options_json
        return JsonResponse(result)

    # POST: Save configurations
    if len(request.body) > MAX_CONFIGURATIONS_BODY_BYTES:
        return JsonResponse({"error": "Request body too large"}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    error = _validate_configurations_payload(data)
    if error:
        return JsonResponse({"error": error}, status=400)

    try:
        for group_id, options in data.items():
            group_id = int(group_id)
            group = next((g for g in DEFAULT_GROUPS if g["id"] == group_id), None)
            if group:
                UserConfiguration.objects.update_or_create(
                    user=request.user,
                    group_id=group_id,
                    defaults={
                        "group_name": group["name"],
                        "options_json": options,
                    }
                )
        return JsonResponse({"success": True})
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid configuration data"}, status=400)


@access_required
@require_http_methods(["GET", "POST"])
def api_get_saved_jobs(request):
    """Get all user saved jobs or save a new job"""
    if request.method == "GET":
        jobs = UserSavedJob.objects.filter(user=request.user)
        return render(request, "abaque/saved_jobs_list.html", {"jobs": jobs})

    # POST: Save a new job
    # SQLite does not enforce max_length, so truncate explicitly.
    name = (request.POST.get("name") or "").strip()[:255] or "Projet sans nom"
    state_raw = request.POST.get("state", "{}")

    if len(state_raw) > MAX_SAVED_JOB_STATE_BYTES:
        return JsonResponse({"error": "State too large"}, status=400)

    if UserSavedJob.objects.filter(user=request.user).count() >= MAX_SAVED_JOBS_PER_USER:
        return JsonResponse({"error": "Too many saved jobs"}, status=400)

    try:
        state_json = json.loads(state_raw)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid state data"}, status=400)

    if not isinstance(state_json, dict):
        return JsonResponse({"error": "Invalid state data"}, status=400)

    job = UserSavedJob.objects.create(
        user=request.user,
        name=name,
        state_json=state_json
    )
    return JsonResponse({"id": job.id, "name": job.name, "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S")})


@access_required
@require_http_methods(["POST"])
def apply_job(request, job_id):
    """Apply a saved job"""
    try:
        job = UserSavedJob.objects.get(id=job_id, user=request.user)
    except UserSavedJob.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)

    state = job.state_json
    if isinstance(state, str):
        # Normalize legacy rows that stored the state as a raw JSON string.
        try:
            state = json.loads(state)
        except json.JSONDecodeError:
            state = {}

    return JsonResponse({
        "state": state,
        "success": True
    })


@access_required
@require_http_methods(["DELETE"])
def api_delete_job(request, job_id):
    """Delete a saved job"""
    try:
        job = UserSavedJob.objects.get(id=job_id, user=request.user)
        job.delete()
        return JsonResponse({"success": True})
    except UserSavedJob.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)
