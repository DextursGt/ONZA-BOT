# Events System Design

**Date:** 2026-02-17
**Author:** Claude (with user collaboration)
**Status:** Approved

## Overview

Comprehensive events system for ONZA-BOT including Join/Leave Messages, Join DM, Auto Roles, Verification, Invite Tracking, and Loyalty Points system with VIP tier management.

## Goals

- Multi-guild configurable event handlers
- Template-based messages with dynamic placeholders
- Invite tracking with fraud detection
- Loyalty/points system integrated with purchases
- Web dashboard for complete admin control
- Modular, maintainable architecture

## Non-Goals

- Real-time WebSocket notifications (Phase 5+)
- Mobile app (future consideration)
- Replacing existing bot_data.json system (supplement only)

---

## 1. Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                        Discord Bot                           │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │ Join Events    │  │ Leave Events   │  │ Auto Roles    │ │
│  └────────┬───────┘  └────────┬───────┘  └───────┬───────┘ │
│           │                    │                   │         │
│  ┌────────┴───────┐  ┌────────┴───────┐  ┌───────┴───────┐ │
│  │ Invite Tracker │  │ Verification   │  │ Loyalty System│ │
│  └────────┬───────┘  └────────┬───────┘  └───────┬───────┘ │
│           │                    │                   │         │
│           └────────────────────┴───────────────────┘         │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │  SQLite Databases   │
                    │  ┌───────────────┐  │
                    │  │  guilds.db    │  │ ← Config
                    │  │  invites.db   │  │ ← Tracking
                    │  │  loyalty.db   │  │ ← Points/VIP
                    │  └───────────────┘  │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │  FastAPI Dashboard  │
                    │  ┌───────────────┐  │
                    │  │ Events Panel  │  │
                    │  │ Stats Panel   │  │
                    │  │ Config Panel  │  │
                    │  └───────────────┘  │
                    └─────────────────────┘
```

### Principles

- **Event-driven:** Each Discord event triggers independent handlers
- **Modular:** Each feature is a separate cog/handler
- **Database-backed:** SQLite for persistence (3 separate databases)
- **No caching:** Bot reads fresh config from DB on each event
- **Fail-safe:** Errors in one handler don't crash others

### Technology Stack

- **Backend:** Python 3.11+, nextcord 2.x, FastAPI
- **Database:** SQLite 3 with aiosqlite
- **Frontend:** Bootstrap 5, vanilla JavaScript
- **Deployment:** pm2 on VPS (193.43.134.31:8000)

---

## 2. Data Model

### Database: guilds.db

**Purpose:** Store per-guild event configuration

```sql
-- Join message configuration
CREATE TABLE join_config (
    guild_id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT 0,
    channel_id TEXT,  -- Discord IDs as strings
    message_template TEXT,
    embed_enabled BOOLEAN DEFAULT 0,
    embed_title TEXT,
    embed_description TEXT,
    embed_color INTEGER,
    embed_image_url TEXT
);

-- Leave message configuration
CREATE TABLE leave_config (
    guild_id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT 0,
    channel_id TEXT,
    message_template TEXT
);

-- Join DM configuration
CREATE TABLE join_dm_config (
    guild_id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT 0,
    message_template TEXT
);

-- Auto roles configuration
CREATE TABLE auto_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    role_id TEXT,
    delay_seconds INTEGER DEFAULT 0
);

-- Verification configuration
CREATE TABLE verification_config (
    guild_id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT 0,
    verification_channel_id TEXT,
    verified_role_id TEXT,
    unverified_role_id TEXT,
    verification_message TEXT,
    timeout_minutes INTEGER DEFAULT 10,
    welcome_after_verify TEXT
);
```

### Database: invites.db

**Purpose:** Track invite usage and detect fraud

```sql
-- Snapshot of guild invites (updated every 5 min)
CREATE TABLE invite_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    code TEXT,
    inviter_id TEXT,
    uses INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Join records
CREATE TABLE join_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id TEXT,
    inviter_id TEXT,
    invite_code TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source TEXT,  -- "invite", "vanity", "unknown", "rejoin", "blacklisted"
    points_awarded BOOLEAN DEFAULT 0
);

-- Blacklist
CREATE TABLE invite_blacklist (
    user_id TEXT PRIMARY KEY,
    reason TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Suspicious activity flags
CREATE TABLE suspicious_invites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id TEXT,
    inviter_id TEXT,
    flag_type TEXT,  -- "new_account", "spam_pattern", "rejoin_spam"
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Database: loyalty.db

**Purpose:** Track points and VIP tiers

```sql
-- User points
CREATE TABLE user_points (
    user_id TEXT PRIMARY KEY,
    points INTEGER DEFAULT 0,
    total_invites INTEGER DEFAULT 0,
    total_spent REAL DEFAULT 0.0,
    current_tier TEXT,  -- "None", "VIP Tier 1", "VIP Tier 2", "VIP Tier 3"
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- VIP tier configuration
CREATE TABLE vip_tiers (
    tier_name TEXT PRIMARY KEY,
    required_points INTEGER,
    role_id TEXT,
    benefits TEXT  -- JSON string
);

-- Points history (audit log)
CREATE TABLE points_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    amount INTEGER,
    reason TEXT,  -- "invite", "purchase", "admin_adjustment"
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Bot Components

### 3.1 JoinEventsHandler (Cog)

```python
class JoinEventsHandler(commands.Cog):
    """Handle member join events"""

    def __init__(self, bot):
        self.bot = bot
        self.db = GuildsDatabase()
        self.template = Template()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Triggered when user joins"""
        guild_id = member.guild.id

        # Load config from DB
        config = await self.db.get_join_config(guild_id)

        if not config or not config['enabled']:
            return

        # Render template
        context = {
            'member': member,
            'guild': member.guild,
            'member_count': member.guild.member_count
        }

        message = self.template.render(config['message_template'], context)

        # Send to channel
        channel = self.bot.get_channel(int(config['channel_id']))
        if channel:
            if config['embed_enabled']:
                embed = nextcord.Embed(
                    title=config['embed_title'],
                    description=message,
                    color=config['embed_color']
                )
                await channel.send(embed=embed)
            else:
                await channel.send(message)
```

### 3.2 LeaveEventsHandler (Cog)

```python
class LeaveEventsHandler(commands.Cog):
    """Handle member leave events"""

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Triggered when user leaves"""
        guild_id = member.guild.id
        config = await self.db.get_leave_config(guild_id)

        if not config or not config['enabled']:
            return

        # Similar rendering logic
        message = self.template.render(config['message_template'], context)
        channel = self.bot.get_channel(int(config['channel_id']))
        await channel.send(message)
```

### 3.3 AutoRolesHandler (Cog)

```python
class AutoRolesHandler(commands.Cog):
    """Auto-assign roles on join"""

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Assign configured auto-roles"""
        guild_id = member.guild.id
        roles_config = await self.db.get_auto_roles(guild_id)

        for role_config in roles_config:
            role = member.guild.get_role(int(role_config['role_id']))
            if role:
                if role_config['delay_seconds'] > 0:
                    await asyncio.sleep(role_config['delay_seconds'])
                await member.add_roles(role)
```

### 3.4 InviteTracker (Cog)

```python
class InviteTracker(commands.Cog):
    """Track invite usage"""

    def __init__(self, bot):
        self.bot = bot
        self.db = InvitesDatabase()
        self.loyalty = LoyaltySystem(bot)
        self.invite_cache = {}
        self.snapshot_task.start()

    @tasks.loop(minutes=5)
    async def snapshot_task(self):
        """Periodic invite snapshot"""
        for guild in self.bot.guilds:
            invites = await guild.invites()
            for invite in invites:
                await self.db.save_snapshot(
                    guild.id, invite.code, invite.inviter.id, invite.uses
                )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Determine who invited the user"""
        guild = member.guild

        # Get current invites
        current_invites = {inv.code: inv.uses for inv in await guild.invites()}
        cached_invites = self.invite_cache.get(guild.id, {})

        # Find which invite was used
        used_code = None
        inviter_id = None

        for code, uses in current_invites.items():
            if code in cached_invites and uses > cached_invites[code]:
                used_code = code
                invite = await self._get_invite_by_code(guild, code)
                inviter_id = invite.inviter.id
                break

        # Update cache
        self.invite_cache[guild.id] = current_invites

        # Check for fake invite
        if inviter_id and await self._is_fake_invite(guild.id, member.id, inviter_id):
            await self.db.add_join_record(
                guild.id, str(member.id), str(inviter_id), used_code, "blacklisted"
            )
            return

        # Valid invite - award points
        if inviter_id:
            await self.loyalty.on_valid_invite(inviter_id)
            await self.db.add_join_record(
                guild.id, str(member.id), str(inviter_id), used_code, "invite", points_awarded=True
            )
```

### 3.5 VerificationHandler (Cog)

```python
class VerificationHandler(commands.Cog):
    """Handle verification system"""

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Start verification process"""
        config = await self.db.get_verification_config(member.guild.id)

        if not config or not config['enabled']:
            return

        # Assign unverified role
        unverified_role = member.guild.get_role(int(config['unverified_role_id']))
        await member.add_roles(unverified_role)

        # Send verification message
        channel = self.bot.get_channel(int(config['verification_channel_id']))
        msg = await channel.send(config['verification_message'])
        await msg.add_reaction('✅')

        # Schedule timeout
        await asyncio.sleep(config['timeout_minutes'] * 60)

        # Check if still unverified
        member = await member.guild.fetch_member(member.id)
        if unverified_role in member.roles:
            await member.kick(reason="Verification timeout")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle verification reaction"""
        if user.bot or str(reaction.emoji) != '✅':
            return

        config = await self.db.get_verification_config(reaction.message.guild.id)

        # Remove unverified, add verified
        unverified_role = reaction.message.guild.get_role(int(config['unverified_role_id']))
        verified_role = reaction.message.guild.get_role(int(config['verified_role_id']))

        await user.remove_roles(unverified_role)
        await user.add_roles(verified_role)

        # Send welcome message
        if config['welcome_after_verify']:
            await reaction.message.channel.send(
                self.template.render(config['welcome_after_verify'], {'member': user})
            )
```

### 3.6 LoyaltySystem

```python
class LoyaltySystem:
    """Manage loyalty points and VIP tiers"""

    POINTS_PER_INVITE = 10
    POINTS_PER_DOLLAR = 1

    def __init__(self, bot):
        self.bot = bot
        self.db = LoyaltyDatabase()

    async def on_valid_invite(self, inviter_id: int):
        """Award points for valid invite"""
        await self.db.add_points(str(inviter_id), self.POINTS_PER_INVITE, "invite")
        await self.check_vip_upgrade(inviter_id)

    async def on_purchase(self, user_id: int, amount: float):
        """Award points for purchase"""
        points = int(amount * self.POINTS_PER_DOLLAR)
        await self.db.add_points(str(user_id), points, "purchase")
        await self.check_vip_upgrade(user_id)

    async def check_vip_upgrade(self, user_id: int):
        """Check and assign VIP tier"""
        user_data = await self.db.get_user_points(str(user_id))
        points = user_data['points']
        current_tier = user_data['current_tier']

        # Determine new tier
        new_tier = None
        if points >= 300:
            new_tier = "VIP Tier 3"
        elif points >= 200:
            new_tier = "VIP Tier 2"
        elif points >= 100:
            new_tier = "VIP Tier 1"

        # Upgrade if needed
        if new_tier and new_tier != current_tier:
            await self.assign_vip_role(user_id, new_tier)
            await self.db.update_tier(str(user_id), new_tier)

    async def assign_vip_role(self, user_id: int, tier: str):
        """Assign VIP role in Discord"""
        tier_config = await self.db.get_vip_tier(tier)
        role_id = int(tier_config['role_id'])

        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member:
                role = guild.get_role(role_id)
                await member.add_roles(role)
```

### 3.7 Template Engine

```python
class Template:
    """Render message templates with placeholders"""

    PLACEHOLDERS = {
        '%member_mention%': lambda ctx: ctx['member'].mention,
        '%member_name%': lambda ctx: ctx['member'].name,
        '%member_tag%': lambda ctx: str(ctx['member']),
        '%member_id%': lambda ctx: ctx['member'].id,
        '%guild_name%': lambda ctx: ctx['guild'].name,
        '%member_count%': lambda ctx: ctx['guild'].member_count,
        '%inviter%': lambda ctx: ctx.get('inviter', {}).get('name', 'Unknown'),
        '%inviter_mention%': lambda ctx: ctx.get('inviter', {}).get('mention', '@Unknown'),
        '%invite_count%': lambda ctx: ctx.get('invite_count', 0),
        '%server_rules%': lambda ctx: ctx.get('rules', 'Ver #reglas'),
        '%verification_emoji%': lambda ctx: '✅',
        '%member_avatar%': lambda ctx: ctx['member'].display_avatar.url
    }

    def render(self, template: str, context: dict) -> str:
        """Render template with context"""
        result = template

        for placeholder, func in self.PLACEHOLDERS.items():
            try:
                value = func(context)
                result = result.replace(placeholder, str(value))
            except (KeyError, AttributeError) as e:
                result = result.replace(placeholder, "[N/A]")
            except Exception as e:
                logger.error(f"Template error for {placeholder}: {e}")
                result = result.replace(placeholder, "[Error]")

        return result
```

---

## 4. API Endpoints

### Events Configuration

```python
# Join messages
GET    /api/events/join/{guild_id}          # Get config
POST   /api/events/join/configure           # Save config
POST   /api/events/join/toggle              # Enable/disable

# Leave messages
GET    /api/events/leave/{guild_id}
POST   /api/events/leave/configure
POST   /api/events/leave/toggle

# Join DM
GET    /api/events/join-dm/{guild_id}
POST   /api/events/join-dm/configure
POST   /api/events/join-dm/toggle

# Auto roles
GET    /api/events/auto-roles/{guild_id}    # List roles
POST   /api/events/auto-roles/add           # Add role
DELETE /api/events/auto-roles/{id}          # Remove role

# Verification
GET    /api/events/verification/{guild_id}
POST   /api/events/verification/configure
POST   /api/events/verification/toggle
```

### Invite Tracking

```python
GET    /api/invites/stats/{guild_id}        # Top inviters
GET    /api/invites/user/{user_id}          # User invite count
POST   /api/invites/blacklist/add           # Add to blacklist
DELETE /api/invites/blacklist/{user_id}     # Remove from blacklist
GET    /api/invites/suspicious/{guild_id}   # Flagged invites
```

### Loyalty System

```python
GET    /api/loyalty/user/{user_id}          # Get points/tier
GET    /api/loyalty/leaderboard              # Top users by points
POST   /api/loyalty/adjust                   # Admin: adjust points manually
GET    /api/loyalty/tiers                    # List VIP tiers
POST   /api/loyalty/tiers/configure          # Configure tier thresholds
```

### Request/Response Models

```python
class JoinConfigRequest(BaseModel):
    guild_id: Union[int, str]
    enabled: bool
    channel_id: Union[int, str]
    message_template: str
    embed_enabled: bool = False
    embed_title: Optional[str] = None
    embed_description: Optional[str] = None
    embed_color: Optional[int] = None

    @field_validator('guild_id', 'channel_id')
    @classmethod
    def convert_ids(cls, v):
        return int(v) if isinstance(v, str) else v

class InviteStatsResponse(BaseModel):
    top_inviters: List[Dict[str, Any]]
    total_invites: int
    total_leaves: int
    net_growth: int
```

---

## 5. Template System

### Available Placeholders

| Placeholder | Description | Example Output |
|-------------|-------------|----------------|
| `%member_mention%` | Mention the user | @Usuario#1234 |
| `%member_name%` | Username only | Usuario |
| `%member_tag%` | Full tag | Usuario#1234 |
| `%member_id%` | User ID | 123456789 |
| `%guild_name%` | Server name | Mi Servidor |
| `%member_count%` | Total members | 1,234 |
| `%inviter%` | Who invited (name) | Invitador |
| `%inviter_mention%` | Who invited (mention) | @Invitador |
| `%invite_count%` | Inviter's total | 42 |
| `%server_rules%` | Rules link | Ver #reglas |
| `%verification_emoji%` | Verification emoji | ✅ |
| `%member_avatar%` | Avatar URL | https://cdn.discord... |

### Example Templates

**Join Message:**
```
¡Bienvenido %member_mention% a **%guild_name%**! 🎉
Ahora somos %member_count% miembros.
Invitado por: %inviter_mention% (Total: %invite_count% invitaciones)
```

**Leave Message:**
```
😢 %member_name% ha dejado el servidor.
Ahora somos %member_count% miembros.
```

**Join DM:**
```
¡Hola %member_name%! 👋
Bienvenido a %guild_name%.

📋 Lee las reglas: %server_rules%
✅ Verifica tu cuenta reaccionando con %verification_emoji%
```

**Verification Message:**
```
%member_mention%, reacciona con ✅ para verificarte y acceder al servidor.
Tienes 10 minutos antes de ser expulsado automáticamente.
```

---

## 6. Loyalty System

### Points Configuration

- **Per valid invite:** 10 points
- **Per dollar spent:** 1 point
- **Manual adjustments:** Admin via dashboard

### VIP Tiers

| Tier | Required Points | Benefits |
|------|----------------|----------|
| VIP Tier 1 | 100 | Rol especial, color personalizado |
| VIP Tier 2 | 200 | Tier 1 + acceso a canales VIP |
| VIP Tier 3 | 300 | Tier 2 + descuentos en tienda |

### Integration with Purchases

```python
# In main.py
async def handle_purchase(self, user_id: int, amount: float, product_id: str):
    """Called when user completes purchase"""
    # Existing purchase logic
    data_manager.add_purchase(user_id, amount, product_id)

    # NEW: Award loyalty points
    await self.loyalty_system.on_purchase(user_id, amount)

    # Check if user upgraded to VIP
    user_data = await self.loyalty_system.db.get_user_points(str(user_id))
    if user_data['current_tier']:
        # Send congratulations DM
        user = await self.fetch_user(user_id)
        await user.send(f"🎉 ¡Felicidades! Alcanzaste {user_data['current_tier']}")
```

---

## 7. Data Flow and Integration

### Event Flow

```
Discord Event → Handler → Multiple Systems
     ↓
on_member_join
     ├→ JoinEventsHandler.on_join()
     │    ├→ guilds.db: Load config
     │    ├→ Template.render(): Process message
     │    └→ channel.send(): Send message
     │
     ├→ AutoRolesHandler.on_join()
     │    ├→ guilds.db: Load roles
     │    └→ member.add_roles(): Assign
     │
     └→ InviteTracker.on_join()
          ├→ invites.db: Compare invites
          ├→ invites.db: Save join record
          ├→ LoyaltySystem.on_valid_invite()
          │    ├→ loyalty.db: Add points
          │    └→ check_vip_upgrade()
          └→ channel.send(): "X invitó a Y"
```

### Dashboard ↔ Bot Synchronization

```
User (Web Panel)
     ↓ POST /api/events/join/configure
FastAPI Endpoint
     ↓ Write to guilds.db
SQLite guilds.db
     ↑ Read on each event (no cache)
Bot Handler (on_member_join)
     ↓ Send message
Discord Channel
```

**Key principle:** No caching. Bot reads fresh config from DB on every event for instant updates.

### Database Independence

**Why 3 separate databases?**

1. **guilds.db** - Configuration only
   - Written by: Dashboard
   - Read by: Bot handlers
   - Frequency: Each event

2. **invites.db** - Invite tracking
   - Written by: Bot (snapshots + joins)
   - Read by: Bot + Dashboard (stats)
   - Frequency: Every 5 min + each join

3. **loyalty.db** - Points/VIP
   - Written by: Bot (invites + purchases)
   - Read by: Bot (VIP checks) + Dashboard (stats)
   - Frequency: Each invite/purchase

**Benefits:**
- Independent backups
- Gradual migration
- Reduced lock contention

---

## 8. Error Handling and Edge Cases

### Invite Tracking Edge Cases

**Unknown inviter:**
```python
# Vanity URL, widget, discovery
if inviter is None:
    await db.add_join_record(
        guild_id, user_id, None, "UNKNOWN", source="unknown"
    )
    # NO loyalty points awarded
```

**Inviter left server:**
```python
# Historical record maintained, no points
inviter_member = guild.get_member(inviter_id)
if inviter_member is None:
    await db.add_join_record(
        guild_id, user_id, inviter_id, code, source="left_server"
    )
```

**Rejoin spam detection:**
```python
# User leaves and rejoins within 5 minutes
last_join = await db.get_last_join(guild_id, user_id)
if last_join and (now - last_join.timestamp).seconds < 300:
    await db.add_join_record(
        guild_id, user_id, inviter_id, code,
        source="rejoin", points_awarded=False
    )
    return  # No points
```

### Fraud Detection

```python
async def _is_fake_invite(self, guild_id, user_id, inviter_id) -> bool:
    """Detect suspicious invites"""

    # Self-invite
    if user_id == inviter_id:
        return True

    # Blacklisted user
    if await self.db.is_blacklisted(user_id):
        return True

    # Account < 7 days old
    user = await self.bot.fetch_user(user_id)
    if (datetime.now() - user.created_at).days < 7:
        await self.db.flag_suspicious(guild_id, user_id, inviter_id, "new_account")
        return True

    # Same inviter, 5+ users in 1 hour
    recent = await self.db.get_recent_invites(guild_id, inviter_id, hours=1)
    if len(recent) >= 5:
        await self.db.flag_suspicious(guild_id, user_id, inviter_id, "spam_pattern")
        return True

    return False
```

### Template Rendering Safety

```python
def render(self, template: str, context: dict) -> str:
    """Safe rendering with fallbacks"""
    result = template

    for placeholder, func in self.PLACEHOLDERS.items():
        try:
            value = func(context)
            result = result.replace(placeholder, str(value))
        except KeyError:
            result = result.replace(placeholder, "[N/A]")
        except AttributeError:
            result = result.replace(placeholder, "[Error]")
        except Exception as e:
            logger.error(f"Placeholder {placeholder}: {e}")
            result = result.replace(placeholder, "[Error]")

    return result
```

### Database Concurrency

```python
async def _execute(self, query: str, params: tuple = ()):
    """Execute with retry on lock"""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, params) as cursor:
                    await db.commit()
                    return cursor
        except aiosqlite.OperationalError as e:
            if "locked" in str(e) and attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (attempt + 1))
                continue
            raise
```

### API Validation

```python
@app.post("/api/events/join/configure")
async def configure_join(request: JoinConfigRequest):
    """Validate before saving"""

    # Channel exists?
    channel = bot_api.bot.get_channel(int(request.channel_id))
    if not channel:
        raise HTTPException(400, "Canal no encontrado")

    # Bot has permissions?
    perms = channel.permissions_for(channel.guild.me)
    if not perms.send_messages:
        raise HTTPException(400, "Sin permisos en ese canal")

    # Template valid?
    try:
        mock_context = {'member': ..., 'guild': ...}
        Template.render(request.message_template, mock_context)
    except Exception as e:
        raise HTTPException(400, f"Template inválido: {e}")

    await db.save_config(request.dict())
    return {"success": True}
```

### Logging Strategy

```python
# Info: Normal operations
logger.info(f"Join message sent: {member.id} in {guild.id}")
logger.info(f"Invite tracked: {inviter_id} -> {member.id} via {code}")
logger.info(f"Loyalty points: +{points} to {user_id}")

# Warning: Expected issues
logger.warning(f"No permissions for join message in {guild.id}")
logger.warning(f"Fake invite detected: {user_id} by {inviter_id}")

# Error: Unexpected failures
logger.error(f"Failed to send join DM to {member.id}: {error}", exc_info=True)
```

---

## 9. Testing Strategy

### Phase 1: Join Messages + Auto Roles

```
Test 1: Basic join message
- Configure in panel
- User joins via invite
- ✓ Message sent to correct channel
- ✓ Placeholders rendered correctly

Test 2: Auto roles
- Configure 2 auto-roles
- User joins
- ✓ Both roles assigned
- ✓ Roles assigned in order

Test 3: Toggle OFF
- Disable join messages
- User joins
- ✓ No message sent
- ✓ Auto roles still work
```

### Phase 2: Invite Tracking

```
Test 1: Basic tracking
- Create invite
- User joins with code
- ✓ Inviter identified
- ✓ Counter incremented
- ✓ Loyalty points awarded

Test 2: Multiple uses
- Same code, 3 users
- ✓ All 3 tracked to same inviter
- ✓ 30 points total awarded

Test 3: Inviter left
- A invites B
- A leaves before B joins
- ✓ Record saved with inviter_id
- ✓ No points awarded

Test 4: Blacklist
- Add user to blacklist
- Blacklisted user joins
- ✓ No points to inviter
- ✓ Record marked "blacklisted"
```

### Phase 3: Leave Messages + Join DM

```
Test 1: Leave message
- Configure leave message
- User leaves
- ✓ Message sent
- ✓ Placeholders work

Test 2: Join DM
- Configure DM
- User joins
- ✓ DM received
- ✓ No error if DMs closed
```

### Phase 4: Verification

```
Test 1: Basic verification
- User joins
- Unverified role assigned
- User reacts ✅
- ✓ Unverified removed
- ✓ Verified assigned
- ✓ Welcome message sent

Test 2: Timeout
- User joins
- No reaction for 10 min
- ✓ User kicked
- ✓ Timeout logged
```

### Loyalty System Testing

```
Test: VIP upgrade
1. User at 0 points
2. Invites 5 users (50 points)
3. ✓ Points = 50
4. Purchases $50 product (50 points)
5. ✓ Points = 100
6. ✓ VIP Tier 1 assigned
7. ✓ Role given in Discord
8. ✓ Congratulations DM sent
```

### Dashboard Testing

```
Test: Configuration persistence
1. Navigate to /events
2. Toggle ON join messages
3. ✓ Saved to guilds.db
4. Restart bot (pm2 restart)
5. ✓ Config persists
6. User joins
7. ✓ Message sent

Test: Statistics
1. Navigate to /stats/invites
2. ✓ Top inviters correct
3. ✓ Total matches DB
4. Filter by date range
5. ✓ Filtered correctly
```

### Verification Commands

```bash
# Check databases created
ls -lh /root/ONZA-BOT/data/*.db

# View schema
sqlite3 /root/ONZA-BOT/data/guilds.db ".schema"

# Last 10 joins
sqlite3 /root/ONZA-BOT/data/invites.db \
  "SELECT * FROM join_records ORDER BY timestamp DESC LIMIT 10"

# User points
sqlite3 /root/ONZA-BOT/data/loyalty.db \
  "SELECT * FROM user_points WHERE user_id = '123456789'"

# Dashboard health
curl http://193.43.134.31:8000/health
```

### Rollback Plan

```bash
# Revert to previous version
git log --oneline -5
git revert <commit-hash>
pm2 restart ONZA-BOT

# Restore DB backup
cp /root/ONZA-BOT/data/guilds.db.backup \
   /root/ONZA-BOT/data/guilds.db
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Create database schemas
- Implement JoinEventsHandler
- Implement AutoRolesHandler
- Basic dashboard UI for configuration
- **Deliverable:** Working join messages + auto roles

### Phase 2: Invite System (Week 2)
- Implement InviteTracker
- Implement LoyaltySystem
- Dashboard for invite stats
- Fraud detection
- **Deliverable:** Full invite tracking + points

### Phase 3: Additional Events (Week 3)
- Implement LeaveEventsHandler
- Implement Join DM functionality
- Dashboard pages for leave/DM config
- **Deliverable:** Complete event coverage

### Phase 4: Verification (Week 4)
- Implement VerificationHandler
- Dashboard verification config
- Testing and refinement
- **Deliverable:** Production-ready verification system

---

## Success Criteria

- ✅ All 6 event types functional (join, leave, DM, auto-roles, verification, invites)
- ✅ Template system with 12 placeholders working
- ✅ Invite tracking with fraud detection operational
- ✅ Loyalty/points system awarding correctly
- ✅ VIP tiers auto-assigned based on points
- ✅ Dashboard configuration persists across bot restarts
- ✅ Zero crashes from event handler errors
- ✅ All tests passing (manual verification checklist)

---

## Future Enhancements (Post-Launch)

- Real-time WebSocket updates in dashboard
- Advanced analytics (growth charts, retention rates)
- Custom placeholder support (user-defined)
- Multi-language template support
- Automated backup system for databases
- Mobile dashboard view
- Role rewards progression system
- Integration with external analytics tools
