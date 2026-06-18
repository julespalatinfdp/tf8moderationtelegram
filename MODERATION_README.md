# 🛡️ Telegram Moderation Bot

Bot de modération complet pour Telegram qui filtre les gros mots, liens externes et spam.

## ✨ Features

- ✅ **Profanity Filter** - Supprime automatiquement les gros mots
- ✅ **Link Filter** - Bloque les liens externes (sauf thefloor8.com & t.me)
- ✅ **Spam Detection** - Détecte et supprime le flood de messages
- ✅ **Warning System** - 3 avertissements avant mute automatique
- ✅ **Auto-Mute** - Mute 10 min après 3 warnings
- ✅ **Database** - Logs persistants des violations
- ✅ **Admin Commands** - Gestion manuelle des utilisateurs

## 🚀 Deployment

### 1. Créer un nouveau bot Telegram

```bash
Ouvre @BotFather dans Telegram
/newbot
Nomme-le : "TheFloor8 Moderation Bot"
Username : @thefloor8_moderation_bot
Récupère le TOKEN
```

### 2. Ajouter le bot au canal

1. Va dans ton canal principal
2. Menu "Info" → "Administrateurs"
3. Ajoute @thefloor8_moderation_bot
4. Donne les permissions :
   - ✅ Delete messages
   - ✅ Ban users
   - ✅ Restrict users

### 3. Deploy sur Railway

1. Crée un repo GitHub avec :
   - moderation_bot.py
   - moderation_requirements.txt
   - Procfile (voir ci-dessous)

2. Va sur railway.app → New Project → Connect GitHub

3. Ajoute les variables d'environnement :
   - `BOT_TOKEN_MODERATION` = ton token BotFather

4. Deploy

### Procfile

```
worker: python moderation_bot.py
```

## 📋 Commandes Admin

```
/mute @username [minutes]       - Mute un utilisateur
/unmute @username               - Unmute un utilisateur
/warnings @username             - Voir les warnings d'un user
/clearwarnings                  - Clear tous les warnings
/modstatus                       - Status de la modération
/help                            - Aide
```

## 🔒 Filtres

### Gros Mots (Banned Words)
- fuck, shit, ass, bitch, damn, hell, crap, etc.
- Case insensitive (fUcK = fuck)
- Peut être customisé facilement

### Liens Externes
- ✅ Autorisés : thefloor8.com, t.me
- ❌ Bloqués : tous les autres domaines
- Regex detection pour toute URL http(s)://

### Spam Detection
- Détecte 5+ messages en 5 secondes
- Automatiquement supprimé
- User averti en DM

## 🎯 Système de Warnings

**Progression :**
1. Message violant → Suppression + Warning #1
2. 2ème violation → Warning #2
3. 3ème violation → Warning #3 + MUTE 10 min

**User reçoit DM :**
```
⚠️ Warning #1

Reason: Profanity detected

You have 2 warnings left before mute.
```

## 📊 Database

Stocke :
- Tous les warnings (user, reason, timestamp, text)
- Muted users (user_id, muted_until, reason)

Queries SQL directes si besoin :
```bash
sqlite3 moderation.db
SELECT * FROM warnings;
SELECT * FROM muted_users;
```

## 🔧 Customization

### Ajouter des mots interdits

Dans `moderation_bot.py`, ligne ~60 :

```python
BANNED_WORDS = [
    r'\bfuck\b', 
    r'\bshit\b',
    r'\bton_mot\b',  # Ajoute le tien ici
]
```

### Changer les domaines whitelist

Ligne ~75 :

```python
ALLOWED_DOMAINS = [
    'thefloor8.com',
    't.me',
    'ton_domaine.com',  # Ajoute ici
]
```

### Changer les seuils

```python
SPAM_THRESHOLD = 5      # messages
SPAM_TIME = 5           # secondes
WARNING_LIMIT = 3       # avant mute
MUTE_DURATION = 10      # minutes
```

## 🐛 Troubleshooting

**Bot ne supprime pas les messages :**
- Vérifier que le bot est admin du canal
- Vérifier les permissions (Delete messages = ON)

**Faux positifs (suppression incorrecte) :**
- Ajouter le mot à une whitelist
- Ajuster les regex patterns

**Performance issues :**
- Réduire SPAM_THRESHOLD
- Augmenter SPAM_TIME

## 📈 Logs

Tous les logs sont visibles dans Railway :
```
[INFO] Database initialized
[WARNING] Banned word from @user: ...
[INFO] user now has 2 warnings
```

## ✅ Checklist

```
☐ Bot créé via @BotFather
☐ Bot ajouté au canal comme admin
☐ Permissions correctes
☐ Deploy sur Railway
☐ BOT_TOKEN_MODERATION set
☐ Test avec gros mots
☐ Test avec liens
☐ Test avec spam
☐ Système de warnings OK
```

---

**Questions ? Besoin d'ajustements ?** 🎯
