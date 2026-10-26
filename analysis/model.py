"""Baseline classifiers (numpy only) and leave-one-session-out evaluation.

LDA with shrinkage is the classic myoelectric-control baseline (Englehart & Hudgins 2003):
no hyper-parameters worth tuning, trains in milliseconds, and robust with few examples.
Multinomial logistic regression is the next step up and gives calibrated probabilities.
"""
import numpy as np


class LDA:
    def __init__(self, shrinkage=0.1):
        self.shrinkage = shrinkage

    def fit(self, X, y):
        self.classes_ = np.unique(y)
        self.mu_ = X.mean(axis=0)
        Xc = X - self.mu_
        means = np.array([Xc[y == c].mean(axis=0) for c in self.classes_])
        R = Xc - means[np.searchsorted(self.classes_, y)]
        S = R.T @ R / max(1, len(X) - len(self.classes_))
        d = S.shape[0]
        S = (1 - self.shrinkage) * S + self.shrinkage * np.trace(S) / d * np.eye(d)
        Si = np.linalg.pinv(S)
        prior = np.array([np.mean(y == c) for c in self.classes_])
        self.W_ = means @ Si                                   # [K, d]
        self.b_ = -0.5 * np.sum(self.W_ * means, axis=1) + np.log(prior)
        return self

    def decision_function(self, X):
        return (X - self.mu_) @ self.W_.T + self.b_

    def predict(self, X):
        return self.classes_[np.argmax(self.decision_function(X), axis=1)]


class LogReg:
    """Multinomial logistic regression, L2, full-batch gradient descent on standardised features."""

    def __init__(self, l2=1e-3, iters=500, lr=0.5):
        self.l2, self.iters, self.lr = l2, iters, lr

    def fit(self, X, y):
        self.classes_ = np.unique(y)
        self.m_, self.s_ = X.mean(0), X.std(0) + 1e-9
        Z = (X - self.m_) / self.s_
        Y = (y[:, None] == self.classes_[None, :]).astype(float)
        n, d = Z.shape
        W, b = np.zeros((d, len(self.classes_))), np.zeros(len(self.classes_))
        for _ in range(self.iters):
            P = self._softmax(Z @ W + b)
            G = P - Y
            W -= self.lr * (Z.T @ G / n + self.l2 * W)
            b -= self.lr * G.mean(0)
        self.W_, self.b_ = W, b
        return self

    @staticmethod
    def _softmax(a):
        a = a - a.max(axis=1, keepdims=True)
        e = np.exp(a)
        return e / e.sum(axis=1, keepdims=True)

    def predict_proba(self, X):
        return self._softmax(((X - self.m_) / self.s_) @ self.W_ + self.b_)

    def predict(self, X):
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


MODELS = {"lda": LDA, "logreg": LogReg}


def confusion(y_true, y_pred, classes):
    idx = {c: i for i, c in enumerate(classes)}
    M = np.zeros((len(classes), len(classes)), int)
    for a, b in zip(y_true, y_pred):
        M[idx[a], idx[b]] += 1
    return M


def trial_vote(y_true, y_pred, trial):
    """Majority vote over the windows of each trial -> (true, predicted) per trial."""
    tt, tp = [], []
    for k in np.unique(trial):
        sel = trial == k
        vals, cnt = np.unique(y_pred[sel], return_counts=True)
        tt.append(y_true[sel][0])
        tp.append(vals[np.argmax(cnt)])
    return np.array(tt), np.array(tp)


def loso(sessions, model="lda", train_sessions=None, **model_kw):
    """Leave-one-session-out. sessions: list of dicts from dataset.windows (the training copy
    may contain rotation-augmented windows: pass them as train_sessions, same order).
    Returns per-session window and trial accuracy, overall confusion matrix and classes."""
    train_sessions = train_sessions or sessions
    classes = np.unique(np.concatenate([s["y"] for s in sessions]))
    res, M = [], np.zeros((len(classes), len(classes)), int)
    for i, test in enumerate(sessions):
        tr = [s for j, s in enumerate(train_sessions) if j != i]
        X = np.concatenate([s["X"] for s in tr])
        y = np.concatenate([s["y"] for s in tr])
        clf = MODELS[model](**model_kw).fit(X, y)
        pred = clf.predict(test["X"])
        tt, tp = trial_vote(test["y"], pred, test["trial"])
        M += confusion(test["y"], pred, classes)
        per_class = [np.mean(pred[test["y"] == c] == c) for c in classes if np.any(test["y"] == c)]
        res.append({"session": test["session"], "window_acc": float(np.mean(pred == test["y"])),
                    "balanced_acc": float(np.mean(per_class)), "trial_acc": float(np.mean(tt == tp)),
                    "n_windows": int(len(pred)), "n_trials": int(len(tt))})
    return {"folds": res, "classes": [str(c) for c in classes], "confusion": M,
            "window_acc": float(np.mean([r["window_acc"] for r in res])),
            "trial_acc": float(np.mean([r["trial_acc"] for r in res]))}


def format_loso(r):
    lines = [f"{'held-out session':<30} {'windows':>8} {'win acc':>8} {'bal acc':>8} {'trials':>7} {'trial acc':>9}"]
    for f in r["folds"]:
        lines.append(f"{f['session'][-30:]:<30} {f['n_windows']:>8} {f['window_acc']:>8.3f} "
                     f"{f['balanced_acc']:>8.3f} {f['n_trials']:>7} {f['trial_acc']:>9.3f}")
    lines.append(f"mean window accuracy {r['window_acc']:.3f}, mean trial (majority vote) accuracy {r['trial_acc']:.3f}")
    w = max(len(c) for c in r["classes"])
    lines.append("confusion (rows = true, cols = predicted, all folds):")
    lines.append(" " * (w + 1) + " ".join(f"{c[:6]:>6}" for c in r["classes"]))
    for c, row in zip(r["classes"], r["confusion"]):
        lines.append(f"{c:>{w}} " + " ".join(f"{v:>6d}" for v in row))
    return "\n".join(lines)
