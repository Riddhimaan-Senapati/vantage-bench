/**
 * Hardcoded admin credentials for CoverageIQ / Vantage
 *
 * SETUP (one-time):
 *   1. Go to https://dashboard.clerk.com and create an application
 *   2. Under "Users", create a user with the email + password below
 *   3. Copy your Publishable Key and Secret Key into .env.local
 *
 * These credentials are the single admin account for the app.
 */
export const CREDENTIALS = {
  email: 'omehta@umass.edu',
  password: 'hackher413',
};
