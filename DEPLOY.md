# Déploiement sur VPS

L'application tourne avec **gunicorn** sur `127.0.0.1:8642` (loopback uniquement), derrière le
nginx déjà en place qui termine le TLS. La base reste **SQLite** et
les fichiers statiques sont servis par l'application elle-même via **WhiteNoise** — nginx n'a
rien d'autre à faire que du proxy.

## Prérequis

- Python ≥ 3.11 et `python3-venv`
- nginx configuré avec un certificat TLS pour le domaine
- Node/npm **inutiles** sur le serveur : `static/css/output.css` est committé

## Installation initiale

```bash
cd /opt
sudo git clone <url-du-depot> abaque
sudo chown -R <utilisateur-de-service>: abaque
cd abaque
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Variables d'environnement

Créer `/etc/abaque.env` (lisible uniquement par root et l'utilisateur de service, `chmod 640`) :

```ini
SECRET_KEY=<clé générée, voir ci-dessous>
DEBUG=false
ALLOWED_HOSTS=abaque.mondomaine.fr
OIDC_CLIENT_ID=<identifiant client>
OIDC_CLIENT_SECRET=<secret client>
OIDC_DISCOVERY_URL=https://sso.mondomaine.fr/.well-known/openid-configuration
```

Générer la clé :

```bash
.venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

⚠️ Avec `DEBUG=false`, l'application **refuse de démarrer** sans `SECRET_KEY` — c'est voulu.

Dans le fournisseur SSO, déclarer l'URI de redirection exacte
`https://abaque.mondomaine.fr/oidc/callback/`. Les endpoints OIDC dépendent du
fournisseur ; remplacer ceux de l'exemple par ses valeurs documentées.

### Base de données et fichiers statiques

```bash
set -a; source /etc/abaque.env; set +a
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py createsuperuser
```

## Service systemd

`/etc/systemd/system/abaque.service` :

```ini
[Unit]
Description=Abaque de la Fabrication Distribuee
After=network.target

[Service]
User=<utilisateur-de-service>
WorkingDirectory=/opt/abaque
EnvironmentFile=/etc/abaque.env
ExecStart=/opt/abaque/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8642 project.wsgi
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now abaque
```

Deux workers suffisent largement ; ne pas en mettre beaucoup plus avec SQLite
(verrous d'écriture).

## nginx

Dans le bloc `server` existant du domaine :

```nginx
location / {
    proxy_pass http://127.0.0.1:8642;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Les deux en-têtes `Host` et `X-Forwarded-Proto` sont **obligatoires** :

- sans `X-Forwarded-Proto`, Django (qui active `SECURE_SSL_REDIRECT` en production)
  ne voit que du HTTP et boucle en redirections infinies ;
- sans `Host`, la vérification CSRF échoue sur tous les formulaires.

Pas de bloc `location /static/` à ajouter : WhiteNoise sert les statiques avec des
noms hachés et un cache long.

## Après la mise en service

1. Se connecter sur `/admin/` avec le compte superuser.
2. L'inscription est **ouverte** (`/register/`) mais les nouveaux comptes n'ont aucun
   accès tant qu'un admin ne les a pas ajoutés au groupe **« Utilisateurs actifs »**
   (admin → Utilisateurs → sélectionner le compte → Groupes).

## Mise à jour

```bash
cd /opt/abaque
git pull
.venv/bin/pip install -r requirements.txt
set -a; source /etc/abaque.env; set +a
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart abaque
```

## Sauvegardes

Toutes les données (comptes, tarifs personnalisés, projets sauvegardés) tiennent dans
`db.sqlite3`. Sauvegarde quotidienne via cron, avec l'outil `sqlite3` (copie cohérente
même si l'application écrit au même moment) :

```cron
0 3 * * * sqlite3 /opt/abaque/db.sqlite3 ".backup /var/backups/abaque-$(date +\%u).sqlite3"
```

(`%u` = jour de la semaine → rotation automatique sur 7 jours.)

## Changer le port

Le port 8642 n'est qu'une convention (le même que le serveur de dev). Pour en changer :
remplacer `8642` dans `abaque.service` (`ExecStart`) et dans le `proxy_pass` nginx, puis
`sudo systemctl daemon-reload && sudo systemctl restart abaque && sudo nginx -s reload`.
