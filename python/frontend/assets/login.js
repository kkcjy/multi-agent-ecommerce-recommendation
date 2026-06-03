const AUTH_STORAGE_KEY = "novacartAuth";
const ADMIN_KEY_STORAGE = "novacartAdminApiKey";
const ADMIN_NAME_STORAGE = "novacartAdminName";

const DEMO_ACCOUNTS = {
  demo_tech: { account: "demo_tech", password: "123456", role: "user", name: "数码极客·张伟", userId: "demo_tech", avatar: "🧑‍💻" },
  demo_student: { account: "demo_student", password: "123456", role: "user", name: "校园达人·李明", userId: "demo_student", avatar: "🎓" },
  demo_worker: { account: "demo_worker", password: "123456", role: "user", name: "都市白领·王芳", userId: "demo_worker", avatar: "👩‍💼" },
  demo_sport: { account: "demo_sport", password: "123456", role: "user", name: "运动达人·赵强", userId: "demo_sport", avatar: "🏃" },
  demo_newbie: { account: "demo_newbie", password: "123456", role: "user", name: "萌新用户·陈静", userId: "demo_newbie", avatar: "🌟" },
  demo_return: { account: "demo_return", password: "123456", role: "user", name: "回归用户·刘洋", userId: "demo_return", avatar: "🔄" },
  admin: { account: "admin", password: "admin123456", role: "admin", name: "管理员", adminKey: "admin123456" },
};

const roleTabs = document.querySelectorAll(".role-tab");
const form = document.getElementById("loginForm");
const accountInput = document.getElementById("loginAccount");
const passwordInput = document.getElementById("loginPassword");
const submitBtn = document.getElementById("loginSubmit");
const state = document.getElementById("loginState");
let selectedRole = "user";

function setRole(role) {
  selectedRole = role;
  roleTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.role === role));
  if (role === "admin") {
    accountInput.value = "admin";
    passwordInput.value = "admin123456";
  } else {
    accountInput.value = "demo_tech";
    passwordInput.value = "123456";
  }
}

function saveAuth(account) {
  const payload = {
    role: account.role,
    account: account.account,
    name: account.name,
    userId: account.userId || "demo_tech",
    loginAt: new Date().toISOString(),
  };
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(payload));
  if (account.role === "user") {
    localStorage.setItem("userId", account.userId || "demo_tech");
  }
  if (account.role === "admin") {
    localStorage.setItem(ADMIN_KEY_STORAGE, account.adminKey);
    localStorage.setItem(ADMIN_NAME_STORAGE, account.name || account.account);
  }
}

async function verifyAdminKey(adminKey) {
  await AppUI.fetchJson("/api/v1/experiments", { headers: { "X-API-Key": adminKey } });
}

async function handleLogin(event) {
  event.preventDefault();
  const accountName = accountInput.value.trim();
  const password = passwordInput.value.trim();
  const matched = Object.values(DEMO_ACCOUNTS).find((item) => item.account === accountName && item.role === selectedRole);

  if (!matched || matched.password !== password) {
    AppUI.setStatus(state, "账号、密码或身份不正确。", "error");
    return;
  }

  AppUI.setButtonBusy(submitBtn, true, "登录中...", "登录");
  AppUI.setStatus(state, "正在登录...", "loading");

  try {
    if (matched.role === "admin") {
      await verifyAdminKey(matched.adminKey);
    }
    saveAuth(matched);
    AppUI.setStatus(state, "登录成功，正在跳转...", "ok");
    window.location.href = matched.role === "admin" ? "/admin" : "/home";
  } catch (error) {
    AppUI.setStatus(state, "管理员校验失败：" + (error.message || "请检查 ECOM_ADMIN_API_KEY"), "error");
  } finally {
    AppUI.setButtonBusy(submitBtn, false, "登录中...", "登录");
  }
}

roleTabs.forEach((tab) => tab.addEventListener("click", () => setRole(tab.dataset.role)));
document.querySelectorAll(".demo-account").forEach((btn) => {
  btn.addEventListener("click", () => {
    setRole(btn.dataset.role);
    accountInput.value = btn.dataset.account;
    passwordInput.value = btn.dataset.password;
  });
});
form.addEventListener("submit", handleLogin);

const initialRole = new URLSearchParams(window.location.search).get("role");
setRole(initialRole === "admin" ? "admin" : "user");
