// English texts: HydraHive app on TVs and tablets (Devices tab).
export const app = {
  title: "HydraHive app", none: "No TV or tablet paired with the app yet.",
  explain: "The app runs on TVs and tablets and connects to HydraHive from there. To pair, enter a name, create a "
    + "code and type it into the app. The code is valid for 15 minutes and only once.",
  name: "Name", name_ph: "e.g. Kitchen tablet", new_code: "Create code", code_for: "Code for \"{{name}}\"",
  code_valid: "valid for {{n}} more min", server: "Server", pin: "Fingerprint",
  code_hint: "The workshop shows the code only now. The app asks for server and code on first start.",
  online: "connected", offline: "not connected", revoked: "revoked",
  notice: "Test message", notice_ph: "Test message, e.g. Someone rang the bell", buttons: "Buttons",
  buttons_ph: "Buttons, e.g. View, Later", send: "Send",
  revoke: "Revoke", remove: "Remove",
  revoke_confirm: "Revoke \"{{name}}\"? The app loses access at once and has to be paired again.",
}

// Fehlertexte (werden in err.* eingemischt).
export const appErr = {
  tvw_app_bad_name: "Please enter a name of at most 40 characters.",
  tvw_app_name_taken: "A paired device already has this name.",
  tvw_app_not_found: "This device does not exist (any more).",
  tvw_app_not_revoked: "Revoke first, then remove.",
  tvw_app_bad_notice: "Please enter a text for the message.",
  tvw_app_code_invalid: "The code is wrong, expired or already used.",
  tvw_app_bad_event: "The app sent an unreadable message.",
  tvw_app_event_too_large: "The message from the app was too large.",
  tvw_app_notice_not_found: "This notice does not exist (any more).",
  tvw_app_bad_answer: "This answer matches no button of the notice.",
}
