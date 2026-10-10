// Invitation and password-reset e-mails can send a person to the home page
// with a one-time login in the part of the address after "#". The public pages
// do not handle logins, so pass that visitor on to the page that does.
// The part after "#" never leaves the browser; nothing is sent anywhere here.

if (/(^#|&)(access_token|error_code)=/.test(window.location.hash)) {
  window.location.replace('/login/nieuw-wachtwoord/' + window.location.hash);
}
