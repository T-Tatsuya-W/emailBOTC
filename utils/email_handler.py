"""Email handler utility.

This module provides `EmailHandler` which can send emails over SMTP and
check for unread messages via IMAP. Configuration is read from a `.env`
file via python-dotenv. Assumed environment variable names:

- EMAIL_ADDRESS - the sending account email address
- EMAIL_APP_PASSWORD - the app password for SMTP/IMAP authentication
- SMTP_SERVER - SMTP server hostname (e.g. smtp.gmail.com)
- SMTP_PORT - SMTP server port (defaults to 587)
- IMAP_SERVER - IMAP server hostname (e.g. imap.gmail.com)
- IMAP_PORT - IMAP server port (defaults to 993)

You may also pass these values to the `EmailHandler` constructor to override
the env values.


Two main public methods
------------------------

send_email(to_address, subject, body, thread_id=None, reply_uid=None) -> bool
		Send a plain-text email. Parameters:
			- to_address: str or None. Destination email address. When `reply_uid`
				is provided the original message is queried and `to_address` may be
				inferred from the original message's Reply-To/From if `to_address` is None.
			- subject: str. Subject line for the message.
			- body: str. Plain-text message body.
			- thread_id: Optional[int]. If provided a synthetic In-Reply-To/References
				header will be created to associate the message with an internal thread id.
			- reply_uid: Optional[int]. IMAP UID of an existing message to reply to;
				when provided the original message headers will be used for threading.

		Returns: True on success. Raises ValueError for invalid inputs (e.g.
		missing to_address when reply_uid is not supplied) or RuntimeError for
		transport/fetch errors.

check_unread(mark_seen: bool = False) -> List[Dict[str, Any]]
		Check the INBOX for unread messages. Parameters:
			- mark_seen: bool. If True, messages returned with numeric UIDs will be
				marked as seen on the server.

		Returns: a list of dictionaries, each containing these keys (example types):
			- 'id' (str): IMAP sequence number (as a string)
			- 'uid' (int|None): IMAP UID (preferred stable identifier)
			- 'from' (str): the From header value
			- 'subject' (str): the Subject header
			- 'date' (str): the Date header
			- 'body' (str): the raw plain-text body extracted from the message
			- 'clean_body' (str): the body cleaned of quoted reply blocks

		Raises RuntimeError for IMAP errors.
"""

from __future__ import annotations

import os
import smtplib
import imaplib
import email
import re
from email.message import EmailMessage
from typing import List, Dict, Optional

from dotenv import load_dotenv


load_dotenv()


class EmailHandler:
	"""Simple email handler to send and check unread emails.

	Constructor arguments override values from the environment. If a
	required value is still missing, methods will raise ValueError.
	"""

	def __init__(
		self,
		email_address: Optional[str] = None,
		app_password: Optional[str] = None,
		smtp_server: Optional[str] = None,
		smtp_port: Optional[int] = None,
		imap_server: Optional[str] = None,
		imap_port: Optional[int] = None,
	) -> None:
		self.email_address = email_address or os.getenv("EMAIL_ADDRESS")
		self.app_password = app_password or os.getenv("EMAIL_APP_PASSWORD")
		self.smtp_server = smtp_server or os.getenv("SMTP_SERVER")
		self.smtp_port = int(smtp_port or os.getenv("SMTP_PORT") or 587)
		self.imap_server = imap_server or os.getenv("IMAP_SERVER")
		self.imap_port = int(imap_port or os.getenv("IMAP_PORT") or 993)

	def _ensure_config(self) -> None:
		missing = []
		if not self.email_address:
			missing.append("EMAIL_ADDRESS")
		if not self.app_password:
			missing.append("EMAIL_APP_PASSWORD")
		if not self.smtp_server:
			missing.append("SMTP_SERVER")
		if not self.imap_server:
			missing.append("IMAP_SERVER")
		if missing:
			raise ValueError(f"Missing email configuration: {', '.join(missing)}")

	def _clean_body(self, body: str) -> str:
		"""Clean a message body by removing quoted reply blocks and leading quote markers.

		This attempts to detect common reply separators such as lines like
		"On Fri, 31 Oct 2025 at 22:48, Name <a@b.com> wrote:" or
		"-----Original Message-----" and truncates the body at that point.
		After truncation it removes any lines that start with '>' (common
		quote marker).
		"""
		if not body:
			return ""

		lines = body.splitlines()
		# patterns that commonly introduce quoted original messages
		patterns = [
			r"^On\s.+wrote:$",
			r"^-----Original Message-----",
			r"^From:\s",
			r"^Sent:\s",
			r"^Subject:\s",
			r"^To:\s",
		]

		cut_index = None
		for i, line in enumerate(lines):
			s = line.strip()
			for pat in patterns:
				try:
					if re.match(pat, s, flags=re.IGNORECASE):
						cut_index = i
						break
				except Exception:
					continue
			if cut_index is not None:
				break

		if cut_index is not None:
			lines = lines[:cut_index]

		# remove quoted lines starting with '>' and strip trailing/leading whitespace
		cleaned = []
		for ln in lines:
			if ln.lstrip().startswith('>'):
				continue
			cleaned.append(ln)

		return "\n".join(cleaned).strip()
	
	def extract_ints_from_body(self, body: str) -> List[int]:
		"""Extract integers from the email body.

		Args:
			body: The plain-text body of the email."""
		ints = re.findall(r'\b\d+\b', body)
		return [int(i) for i in ints]
	

	def send_email(
		self,
		to_address: Optional[str],
		subject: str,
		body: str,
		thread_id: Optional[int] = None,
		reply_uid: Optional[int] = None,
	) -> bool:
		"""Send an email.

		Args:
			to_address: destination email address (may be None when replying by uid)
			subject: subject line
			body: plain-text message body

			thread_id: optional integer thread identifier. If provided, the
				function will set synthetic `In-Reply-To`/`References` headers
				so clients can associate this message with an internal thread id.

			reply_uid: optional IMAP UID of an existing message in the INBOX.
				When provided the function will fetch the original message by
				UID, extract its Message-ID and Reply-To/From, and use those
				values to set In-Reply-To/References and default recipient.
				This is the recommended way to send a stable, in-thread reply.

		Returns:
			True on success.

		Raises:
			ValueError if configuration is missing.
			RuntimeError for SMTP/connection errors.
		"""
		self._ensure_config()

		# allow to_address to be None when reply_uid will supply the recipient
		if to_address is not None and (not isinstance(to_address, str) or not to_address):
			raise ValueError("to_address must be a non-empty string or None when reply_uid is used")

		msg = EmailMessage()
		msg["From"] = self.email_address
		msg["To"] = to_address

		# Ensure subject preserves threading convention
		final_subject = subject or ""

		# If reply_uid is provided, fetch original message to extract headers
		if reply_uid is not None:
			try:
				with imaplib.IMAP4_SSL(self.imap_server, self.imap_port) as imap:
					imap.login(self.email_address, self.app_password)
					imap.select('INBOX')
					typ, msg_data = imap.uid('fetch', str(int(reply_uid)), '(RFC822)')
					if typ == 'OK' and msg_data:
						raw = None
						for part in msg_data:
							if isinstance(part, tuple):
								raw = part[1]
								break
						if raw:
							orig = email.message_from_bytes(raw)
							orig_msg_id = orig.get('Message-ID')
							orig_refs = orig.get('References', '')
							orig_reply_to = orig.get('Reply-To') or orig.get('From')
							# set default recipient if not provided
							if not to_address and orig_reply_to:
								to_address = orig_reply_to
							# set threading headers from original
							if orig_msg_id:
								try:
									msg['In-Reply-To'] = orig_msg_id
									# append to existing refs if present
									refs = (orig_refs + ' ' + orig_msg_id).strip() if orig_refs else orig_msg_id
									msg['References'] = refs
								except Exception:
									pass
					try:
						imap.logout()
					except Exception:
						pass
			except Exception as exc:
				raise RuntimeError(f"Failed to fetch message for reply_uid={reply_uid}: {exc}")

		if thread_id is not None:
			# prefix Re: if not present
			if not final_subject.lower().startswith("re:"):
				final_subject = "Re: " + final_subject

			# construct a synthetic message-id using the sender domain when possible
			domain = "local"
			try:
				if self.email_address and "@" in self.email_address:
					domain = self.email_address.split("@", 1)[1]
				elif self.smtp_server:
					domain = str(self.smtp_server).split(":", 1)[0]
			except Exception:
				domain = "local"

			synthetic_id = f"<thread-{int(thread_id)}@{domain}>"
			try:
				# only set synthetic headers if they aren't already set by reply_uid handling
				if 'In-Reply-To' not in msg:
					msg["In-Reply-To"] = synthetic_id
				if 'References' not in msg:
					msg["References"] = synthetic_id
			except Exception:
				pass

		msg["Subject"] = final_subject
		msg.set_content(body or "")

		try:
			with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as smtp:
				# Start TLS if using the usual submission port
				try:
					smtp.starttls()
				except Exception:
					# Some servers may not require/allow starttls; ignore if it fails
					pass
				smtp.login(self.email_address, self.app_password)
				smtp.send_message(msg)
		except Exception as exc:  # pragma: no cover - environment-specific
			raise RuntimeError(f"Failed to send email: {exc}")

		return True

	def check_unread(self, mark_seen: bool = False) -> List[Dict[str, str]]:
		"""Check for unread messages in INBOX.

		Args:
			mark_seen: if True, mark messages as seen on the server.

		Returns:
			A list of dictionaries with keys: 'id', 'uid', 'from', 'subject', 'date', body', 'clean_body'.
			- 'id' is the IMAP sequence number (string).
			- 'uid' is the IMAP UID (int) which is the stable identifier you should
			  prefer if you need to refer to the same message later across sessions.

		Raises:
			ValueError if configuration is missing.
			RuntimeError for IMAP/connection errors.
		"""
		self._ensure_config()

		results: List[Dict[str, str]] = []

		try:
			# Use SSL IMAP
			with imaplib.IMAP4_SSL(self.imap_server, self.imap_port) as imap:
				imap.login(self.email_address, self.app_password)
				imap.select("INBOX")

				# We'll request both sequence numbers and UIDs for unseen messages
				# Sequence numbers are useful for immediate session ops; UIDs are
				# stable across sessions and are recommended for long-term references.
				typ_seq, data_seq = imap.search(None, "UNSEEN")
				if typ_seq != "OK":
					return results
				ids_seq = data_seq[0].split() if data_seq and data_seq[0].strip() else []

				# UID search
				typ_uid, data_uid = imap.uid('search', None, 'UNSEEN')
				if typ_uid != 'OK':
					# fall back to sequence-only handling
					uids = []
				else:
					uids = data_uid[0].split() if data_uid and data_uid[0].strip() else []

				# iterate zipped lists; if lengths differ we iterate over available pairs
				for seq_num, uid in zip(ids_seq, uids if uids else ids_seq):
					# fetch by UID when available to be robust
					if uids:
						typ, msg_data = imap.uid('fetch', uid, "(RFC822)")
					else:
						typ, msg_data = imap.fetch(seq_num, "(RFC822)")
					if typ != "OK":
						continue
					# msg_data is a list of tuples; find the part containing the raw message
					raw = None
					for part in msg_data:
						if isinstance(part, tuple):
							raw = part[1]
							break
					if not raw:
						continue

					parsed = email.message_from_bytes(raw)
					frm = parsed.get("From", "")
					subj = parsed.get("Subject", "")
					date = parsed.get("Date", "")

					# extract the full plain-text body when possible
					body = ""
					if parsed.is_multipart():
						for part in parsed.walk():
							ctype = part.get_content_type()
							cdisp = str(part.get("Content-Disposition") or "")
							if ctype == "text/plain" and "attachment" not in cdisp:
								try:
									body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
								except Exception:
									body = ""
								break
					else:
						try:
							body = parsed.get_payload(decode=True).decode(parsed.get_content_charset() or "utf-8", errors="replace")
						except Exception:
							body = ""

					body = (body or "").strip()

					# clean the body by removing quoted blocks and quoted lines
					clean_body = self._clean_body(body)

					results.append({
						"id": seq_num.decode() if isinstance(seq_num, bytes) else str(seq_num),
						"uid": int(uid) if isinstance(uid, (bytes, bytearray)) or (isinstance(uid, str) and uid.isdigit()) else (int(uid) if isinstance(uid, str) and uid.isdigit() else None),
						"from": frm,
						"subject": subj,
						"date": date,
						"body": body,
						"clean_body": clean_body,
					})

					if mark_seen:
						# mark as seen. Prefer UID STORE when we have a UID, otherwise use sequence STORE.
						try:
							if uids:
								imap.uid('store', uid, '+FLAGS', '\\Seen')
							else:
								imap.store(seq_num, '+FLAGS', '\\Seen')
						except Exception:
							# best-effort, ignore marking failures
							pass

				imap.logout()
		except Exception as exc:  # pragma: no cover - environment-specific
			raise RuntimeError(f"Failed to check unread messages: {exc}")

		return results





__all__ = ["EmailHandler"]

