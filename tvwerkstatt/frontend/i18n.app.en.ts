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
  code_hint_pin: "When pairing, the app shows a fingerprint. It must look exactly like this one, otherwise cancel.",
  build: "Build app", build_again: "Rebuild app", download: "Download app",
  build_none: "The app has not been built yet. It takes about a minute, nothing happens on the TV.",
  build_need_setup: "Building works once the workshop is set up.",
  build_running: "Building app … step {{n}} of {{total}}", built: "Built: version {{v}}",
  download_hint: "To install by hand, e.g. on a tablet: copy the file to the device and open it there. "
    + "The device asks once whether to allow apps from this source.",
  bstep: {
    container: "Start build environment", fetch: "Get tools", verify: "Check tools", unpack: "Transfer source",
    build: "Test and build", collect: "Check result",
  },
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
  tvw_app_no_build: "The app has not been built yet.",
  tvw_app_build_perms: "The built app asks for other permissions than expected. It is not offered.",
  tvw_app_build_too_large: "The built app is unexpectedly large. It is not offered.",
  tvw_app_build_tests: "The app's checks failed or did not run. It is not offered.",
}
