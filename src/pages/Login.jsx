function Login({ onLogin }) {
  return (
    <div className="login-page">
      <div className="login-card">

        <div className="login-logo">
          <div className="logo-icon">I</div>
          <div>
            <h1>IBVAP</h1>
            <span>Border Analytics</span>
          </div>
        </div>

        <h2>Secure Command Center</h2>
        <p className="login-subtitle">
          Sign in to access the border surveillance platform
        </p>

        <div className="login-form">
          <label>Username</label>
          <input
            type="text"
            placeholder="Enter username"
          />

          <label>Password</label>
          <input
            type="password"
            placeholder="Enter password"
          />

          <button onClick={onLogin}>
            Sign In
          </button>
        </div>

        <p className="login-security">
          🔒 Authorized personnel only
        </p>

      </div>
    </div>
  );
}

export default Login;