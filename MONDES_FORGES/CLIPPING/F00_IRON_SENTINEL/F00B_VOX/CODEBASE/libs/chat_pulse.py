#!/usr/bin/env python3
"""
chat_pulse — Le Radar de VOX (branche v2-live).

Le VOD est le passé. Le live est maintenant. Le Radar écoute le chat.

Principe (inspiré du watcher CutChain, réécrit 100% stdlib — doctrine F00B) :
- Une connexion IRC anonyme par chaîne (justinfan, aucun token requis)
- Vitesse de chat mesurée par tranche de 10s
- Baseline EMA glissante sur 5 minutes (ce qui est "normal" pour cette chaîne)
- Mots chauds des 30 dernières secondes
- Clip pressure : nombre de messages du type "clip it / coupe / CLIP"
- Un MOMENT se déclenche quand :
    taux >= max(min_rate, spike_factor × baseline)   OU   clip_pressure >= seuil
  avec warm-up 30s après connexion et cooldown 120s par chaîne.

Chaque moment est un dict :
  {channel, platform, detected_at, start_epoch, end_epoch, rate, baseline,
   intensity, hot_words, clip_pressure}

Hérésies interdites :
❌ Aucune dépendance pip (socket + ssl + threading uniquement)
❌ Aucun token Twitch pour la LECTURE du chat
❌ Jamais deux moments à moins de cooldown_sec sur la même chaîne
"""

import re
import ssl
import socket
import threading
import time
from collections import Counter, deque

IRC_HOST = "irc.chat.twitch.tv"
IRC_PORT = 6697

# Motifs "clip it" — FR + EN
CLIP_PATTERNS = re.compile(
    r"\b(clips?|clip it|coupe|coupez|c'est un clip|clip that|moment|w clip|l clip)\b",
    re.IGNORECASE,
)

WORD_SPLIT = re.compile(r"[^a-zàâçéèêëîïôûùüÿñæœ0-9']+", re.IGNORECASE)


class ChannelMonitor(threading.Thread):
    """Écoute le chat d'UNE chaîne Twitch et détecte les moments."""

    def __init__(self, channel, config, out_queue, stop_event):
        super().__init__(daemon=True, name=f"pulse-{channel}")
        self.channel = channel.lower().lstrip("#")
        self.cfg = config
        self.out_queue = out_queue
        self.stop_event = stop_event

        self.msg_times = deque(maxlen=4000)          # timestamps des messages
        self.rate_samples = deque(maxlen=60)        # (epoch, rate_10s) — 5 min @ 1/10s
        self.msg_texts = deque(maxlen=400)          # (epoch, texte) — mots chauds
        self.moments_count = 0
        self.last_moment_at = None
        self.connected = False
        self.msgs_total = 0

        self._cooldown_until = 0.0
        self._warmup_until = time.time() + config.get("warmup_sec", 30)

    # ── Connexion IRC ────────────────────────────────────────────────────────
    def _connect(self):
        raw = socket.create_connection((IRC_HOST, IRC_PORT), timeout=15)
        ctx = ssl.create_default_context()
        sock = ctx.wrap_socket(raw, server_hostname=IRC_HOST)
        nick = f"justinfan{int(time.time()) % 100000}"
        sock.sendall(f"NICK {nick}\r\n".encode())
        sock.sendall(f"JOIN #{self.channel}\r\n".encode())
        return sock

    def _reconnect_backoff(self, attempt):
        self.connected = False
        delay = min(60, 5 * attempt)
        log_line(f"[{self.channel}] reconnect dans {delay}s (tentative {attempt})")
        for _ in range(delay):
            if self.stop_event.is_set():
                return False
            time.sleep(1)
        return True

    # ── Mesures ──────────────────────────────────────────────────────────────
    def _rate_10s(self, now):
        window = now - 10.0
        while self.msg_times and self.msg_times[0] < window:
            self.msg_times.popleft()
        return len(self.msg_times)

    def _baseline(self, now, current_rate):
        """Moyenne des taux échantillonnés sur les 5 dernières minutes."""
        # Échantillonner au plus 1 fois par 10s
        if not self.rate_samples or now - self.rate_samples[-1][0] >= 10.0:
            self.rate_samples.append((now, current_rate))
        window = now - self.cfg.get("baseline_window_sec", 300)
        while self.rate_samples and self.rate_samples[0][0] < window:
            self.rate_samples.popleft()
        if len(self.rate_samples) < 6:
            return None  # baseline pas encore fiable
        return sum(r for _, r in self.rate_samples) / len(self.rate_samples)

    def _hot_words(self, now):
        window = now - 30.0
        counter = Counter()
        while self.msg_texts and self.msg_texts[0][0] < window:
            self.msg_texts.popleft()
        for _, text in self.msg_texts:
            for w in WORD_SPLIT.split(text.lower()):
                if len(w) >= 4:
                    counter[w] += 1
        return [w for w, _ in counter.most_common(5)]

    def _clip_pressure(self, now):
        window = now - 30.0
        return sum(1 for ts, text in list(self.msg_texts)[-60:]
                   if ts >= window and CLIP_PATTERNS.search(text))

    # ── Détection ────────────────────────────────────────────────────────────
    def _check_moment(self, now, rate, baseline):
        if now < self._warmup_until:
            return None
        if now < self._cooldown_until:
            return None

        spike_ok = baseline is not None and rate >= max(
            self.cfg.get("min_rate", 8),
            self.cfg.get("spike_factor", 3.0) * baseline,
        )
        pressure_ok = self._clip_pressure(now) >= self.cfg.get("pressure_threshold", 4)

        if not (spike_ok or pressure_ok):
            return None

        ratio = rate / max(baseline, 0.5) if baseline else 3.0
        intensity = min(1.0, round(ratio / 3.0, 2)) if ratio >= 1 else round(rate / 10, 2)

        moment = {
            "channel": self.channel,
            "platform": "twitch",
            "detected_at": round(now, 2),
            "start_epoch": round(now - self.cfg.get("pre_roll_sec", 10), 2),
            "end_epoch": round(now + self.cfg.get("post_roll_sec", 30), 2),
            "rate": rate,
            "baseline": round(baseline, 2) if baseline is not None else None,
            "intensity": intensity,
            "hot_words": self._hot_words(now),
            "clip_pressure": self._clip_pressure(now),
            "trigger": "chat_spike" if spike_ok else "clip_pressure",
        }
        self.moments_count += 1
        self.last_moment_at = now
        self._cooldown_until = now + self.cfg.get("cooldown_sec", 120)
        return moment

    # ── Boucle principale ────────────────────────────────────────────────────
    def run(self):
        attempt = 0
        sock = None
        while not self.stop_event.is_set():
            try:
                if sock is None:
                    sock = self._connect()
                    self.connected = True
                    attempt = 0
                    log_line(f"[{self.channel}] connecté à {IRC_HOST}:{IRC_PORT}")

                sock.settimeout(5.0)
                buf = b""
                while not self.stop_event.is_set():
                    try:
                        chunk = sock.recv(4096)
                    except socket.timeout:
                        self._tick(time.time())
                        continue
                    if not chunk:
                        raise ConnectionError("flux fermé")
                    buf += chunk
                    while b"\r\n" in buf:
                        line, buf = buf.split(b"\r\n", 1)
                        pong = self._handle_line(line.decode("utf-8", "replace"))
                        if pong:
                            sock.sendall(pong.encode())
                        self._tick(time.time())
            except Exception as exc:  # noqa: BLE001 — le radar ne meurt jamais
                log_line(f"[{self.channel}] erreur : {exc}")
                try:
                    if sock:
                        sock.close()
                except OSError:
                    pass
                sock = None
                attempt += 1
                if not self._reconnect_backoff(attempt):
                    break
        self.connected = False

    def _handle_line(self, line):
        """Retourne la chaîne PONG si un PING doit être acquitté."""
        if line.startswith("PING"):
            return "PONG :tmi.chat.twitch.tv\r\n"
        if "PRIVMSG #" not in line:
            return None
        try:
            head, payload = line.split("PRIVMSG ", 1)
            chan_part, text = payload.split(" :", 1) if " :" in payload else (payload, "")
            text = text.strip()
        except ValueError:
            return None
        if not text:
            return None
        now = time.time()
        # Timestamp serveur si dispo (tags tmi-sent-ts)
        m = re.search(r"tmi-sent-ts=(\d+)", head)
        ts = int(m.group(1)) / 1000.0 if m else now
        self.msg_times.append(min(ts, now))
        self.msg_texts.append((now, text))
        self.msgs_total += 1
        return None

    def _tick(self, now):
        rate = self._rate_10s(now)
        baseline = self._baseline(now, rate)
        moment = self._check_moment(now, rate, baseline)
        if moment:
            log_line(
                f"[{self.channel}] 🔥 MOMENT — rate={rate} baseline={moment['baseline']} "
                f"intensité={moment['intensity']} trigger={moment['trigger']}"
            )
            try:
                self.out_queue.put_nowait(moment)
            except Exception:  # queue pleine : on n'alourdit pas
                pass

    def snapshot(self, now=None):
        now = now or time.time()
        rate = self._rate_10s(now)
        baseline = self._baseline(now, rate)
        return {
            "channel": self.channel,
            "connected": self.connected,
            "msgs_total": self.msgs_total,
            "rate_10s": rate,
            "baseline": round(baseline, 2) if baseline is not None else None,
            "clip_pressure": self._clip_pressure(now),
            "hot_words": self._hot_words(now),
            "moments": self.moments_count,
            "last_moment_at": self.last_moment_at,
            "cooldown_until": self._cooldown_until,
        }


class Radar:
    """Multi-chaînes : un ChannelMonitor par chaîne, une queue partagée."""

    def __init__(self, twitch_channels, config=None, kick_channels=None):
        self.cfg = {
            "min_rate": 8,
            "spike_factor": 3.0,
            "pressure_threshold": 4,
            "cooldown_sec": 120,
            "warmup_sec": 30,
            "baseline_window_sec": 300,
            "pre_roll_sec": 10,
            "post_roll_sec": 30,
        }
        if config:
            self.cfg.update(config)
        self.out_queue = __import__("queue").Queue(maxsize=500)
        self.stop_event = threading.Event()
        self.monitors = []
        for ch in twitch_channels or []:
            m = ChannelMonitor(ch, self.cfg, self.out_queue, self.stop_event)
            self.monitors.append(m)
        self.kick_channels = kick_channels or []  # v2.1 — Kick (Pusher public)

    def start(self):
        for m in self.monitors:
            m.start()
        return self

    def drain(self, block_timeout=5.0):
        """Récupère les moments disponibles (bloque jusqu'à timeout si vide)."""
        moments = []
        try:
            moments.append(self.out_queue.get(timeout=block_timeout))
        except Exception:
            return moments
        while True:
            try:
                moments.append(self.out_queue.get_nowait())
            except Exception:
                break
        return moments

    def snapshot(self):
        now = time.time()
        return [m.snapshot(now) for m in self.monitors]

    def stop(self):
        self.stop_event.set()


def log_line(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
