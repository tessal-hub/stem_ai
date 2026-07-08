import numpy as np

def inspect_embedding_space(encoder, X, y, class_names, save_path='embedding_space.png'):
    try:
        from sklearn.manifold import TSNE
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("Cần cài đặt scikit-learn và matplotlib để vẽ TSNE.")
        return None, None

    print("Đang tính embeddings...")
    embeddings = encoder.predict(X, verbose=0)
    
    print("Đang chiếu xuống 2D (mất vài giây)...")
    tsne = TSNE(
        n_components=2,
        perplexity=min(30, max(5, len(X) // 10)),
        random_state=42,
        max_iter=1000
    )
    coords_2d = tsne.fit_transform(embeddings)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    colors = plt.cm.tab10(np.linspace(0, 1, len(class_names)))
    
    ax = axes[0]
    for i, (name, color) in enumerate(zip(class_names, colors)):
        mask = (y == i)
        if not np.any(mask): continue
        ax.scatter(coords_2d[mask, 0], coords_2d[mask, 1],
                  c=[color], label=name, alpha=0.6, s=20)
        
        cx, cy = coords_2d[mask, 0].mean(), coords_2d[mask, 1].mean()
        ax.annotate(name, (cx, cy), fontsize=9, fontweight='bold',
                   ha='center',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor=color, alpha=0.3))
    
    ax.set_title('Toàn bộ Embedding Space')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    ax = axes[1]
    hard_pairs = [
        (class_names.index('CIRCLE_CW') if 'CIRCLE_CW' in class_names else -1, 'CIRCLE_CW', colors[0]),
        (class_names.index('CIRCLE_CCW') if 'CIRCLE_CCW' in class_names else -1, 'CIRCLE_CCW', colors[1]),
        (class_names.index('SWIPE_RIGHT') if 'SWIPE_RIGHT' in class_names else -1, 'SWIPE_RIGHT', colors[2]),
        (class_names.index('SWIPE_UP') if 'SWIPE_UP' in class_names else -1, 'SWIPE_UP', colors[3]),
    ]
    for class_idx, name, color in hard_pairs:
        if class_idx == -1: continue
        mask = (y == class_idx)
        if not np.any(mask): continue
        ax.scatter(coords_2d[mask, 0], coords_2d[mask, 1],
                  c=[color], label=name, alpha=0.7, s=30)
    
    ax.set_title('Zoom vào các cặp dễ nhầm')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Đã lưu ảnh TSNE tại: {save_path}")
    return embeddings, coords_2d


def compute_distance_ratio(encoder, X, y, class_names):
    embeddings = encoder.predict(X, verbose=0)
    
    intra_distances = []
    inter_distances = []
    
    classes = np.unique(y)
    
    for c in classes:
        class_embs = embeddings[y == c]
        other_embs = embeddings[y != c]
        
        n = len(class_embs)
        if n >= 2:
            idx_a = np.random.choice(n, min(200, n*(n-1)//2), replace=True)
            idx_b = np.random.choice(n, min(200, n*(n-1)//2), replace=True)
            mask = idx_a != idx_b
            if np.any(mask):
                diffs = class_embs[idx_a[mask]] - class_embs[idx_b[mask]]
                intra_distances.extend(np.linalg.norm(diffs, axis=1).tolist())
        
        if len(class_embs) > 0 and len(other_embs) > 0:
            idx_a = np.random.choice(len(class_embs), min(200, len(class_embs)), replace=True)
            idx_b = np.random.choice(len(other_embs), min(200, len(other_embs)), replace=True)
            diffs = class_embs[idx_a] - other_embs[idx_b]
            inter_distances.extend(np.linalg.norm(diffs, axis=1).tolist())
    
    d_intra = np.mean(intra_distances) if intra_distances else 0.0
    d_inter = np.mean(inter_distances) if inter_distances else 1.0
    ratio = d_intra / d_inter if d_inter > 0 else 0.0
    
    print("\n=== DISTANCE ANALYSIS ===")
    print(f"  Intra-class distance (muốn NHỎ): {d_intra:.4f}")
    print(f"  Inter-class distance (muốn LỚN): {d_inter:.4f}")
    print(f"  Ratio (muốn < 0.5):              {ratio:.4f}")
    
    if ratio < 0.3:
        verdict = "✅ RẤT TỐT — Encoder phân biệt tốt"
    elif ratio < 0.5:
        verdict = "✅ TỐT — Dùng được"
    elif ratio < 0.7:
        verdict = "⚠️  TRUNG BÌNH — Nên train thêm"
    else:
        verdict = "❌ KÉM — Encoder chưa học được"
    
    print(f"  Đánh giá: {verdict}")
    return float(ratio)


def per_class_diagnosis(encoder, X, y, class_names):
    embeddings = encoder.predict(X, verbose=0)
    
    print("\n=== PER-CLASS DIAGNOSIS ===")
    print(f"{'Class':<15} {'Intra-dist':>12} {'Nearest Wrong Class':<25} {'Overlap Risk'}")
    print("-" * 70)
    
    classes = np.unique(y)
    
    for c in classes:
        name = class_names[c]
        class_embs = embeddings[y == c]
        if len(class_embs) == 0: continue
        
        centroid = class_embs.mean(axis=0)
        diffs = class_embs - centroid
        intra = np.linalg.norm(diffs, axis=1).mean()
        
        nearest_class_name = "?"
        nearest_dist = float('inf')
        for other_c in classes:
            if other_c == c:
                continue
            other_embs = embeddings[y == other_c]
            if len(other_embs) == 0: continue
            other_centroid = other_embs.mean(axis=0)
            d = np.linalg.norm(centroid - other_centroid)
            if d < nearest_dist:
                nearest_dist = d
                nearest_class_name = class_names[other_c]
        
        if nearest_dist == float('inf') or nearest_dist == 0:
            risk = 0.0
        else:
            risk = intra / (nearest_dist / 2)
        risk_label = "✅ OK" if risk < 0.7 else ("⚠️ WARN" if risk < 1.0 else "❌ OVERLAP")
        
        print(f"{name:<15} {intra:>12.4f} {nearest_class_name:<25} {risk_label}")


def few_shot_evaluation(encoder, X, y, class_names, n_support=10, n_query=30, n_episodes=100):
    episode_accuracies = []
    classes = np.unique(y)
    
    for episode in range(n_episodes):
        eligible_classes = [c for c in classes if len(np.where(y == c)[0]) > n_support]
        if len(eligible_classes) < 4:
            return 0.0, 0.0
        
        episode_classes = np.random.choice(eligible_classes, size=4, replace=False)
        
        support_embeddings = {}
        query_X, query_y = [], []
        
        for c in episode_classes:
            class_indices = np.where(y == c)[0]
            np.random.shuffle(class_indices)
            
            support_idx = class_indices[:n_support]
            support_embs = encoder.predict(X[support_idx], verbose=0)
            support_embeddings[c] = support_embs.mean(axis=0)
            
            query_idx = class_indices[n_support:n_support + n_query]
            if len(query_idx) > 0:
                query_X.extend(X[query_idx])
                query_y.extend([c] * len(query_idx))
        
        if len(query_X) == 0:
            continue
            
        query_X = np.array(query_X)
        query_embeddings = encoder.predict(query_X, verbose=0)
        
        correct = 0
        for i, emb in enumerate(query_embeddings):
            distances = {
                c: np.linalg.norm(emb - proto)
                for c, proto in support_embeddings.items()
            }
            predicted = min(distances, key=distances.get)
            if predicted == query_y[i]:
                correct += 1
        
        accuracy = correct / len(query_y)
        episode_accuracies.append(accuracy)
    
    if not episode_accuracies:
        return 0.0, 0.0
        
    mean_acc = np.mean(episode_accuracies)
    std_acc  = np.std(episode_accuracies)
    
    print(f"\n=== FEW-SHOT EVALUATION ({n_support} mẫu) ===")
    print(f"  Setup: {n_support} mẫu để đăng ký, test trên {n_query} mẫu/spell")
    print(f"  Accuracy: {mean_acc:.1%} ± {std_acc:.1%}  (trên {n_episodes} episodes)")
    
    thresholds = [
        (0.90, "✅ XUẤT SẮC — Sẵn sàng deploy"),
        (0.80, "✅ TỐT — Dùng được trong thực tế"),
        (0.70, "⚠️  TRUNG BÌNH — Nên cải thiện"),
        (0.00, "❌ KÉM — Cần xem lại dữ liệu và architecture"),
    ]
    for threshold, label in thresholds:
        if mean_acc >= threshold:
            print(f"  Đánh giá: {label}")
            break
    
    return float(mean_acc), float(std_acc)


def full_encoder_evaluation(encoder, X, y, class_names, save_path):
    print("\n" + "=" * 60)
    print("ENCODER EVALUATION REPORT")
    print("=" * 60)
    
    inspect_embedding_space(encoder, X, y, class_names, save_path=save_path)
    
    ratio = compute_distance_ratio(encoder, X, y, class_names)
    per_class_diagnosis(encoder, X, y, class_names)
    
    print("\n--- Test với 5 mẫu/spell ---")
    acc_5, std_5 = few_shot_evaluation(encoder, X, y, class_names, n_support=5)
    
    print("\n--- Test với 10 mẫu/spell ---")
    acc_10, std_10 = few_shot_evaluation(encoder, X, y, class_names, n_support=10)
    
    print("\n--- Test với 20 mẫu/spell ---")
    acc_20, std_20 = few_shot_evaluation(encoder, X, y, class_names, n_support=20)
    
    print("\n" + "=" * 60)
    print("TÓM TẮT")
    print(f"  Distance Ratio:      {ratio:.3f}")
    print(f"  Few-shot (5 mẫu):    {acc_5:.1%} ± {std_5:.1%}")
    print(f"  Few-shot (10 mẫu):   {acc_10:.1%} ± {std_10:.1%}")
    print(f"  Few-shot (20 mẫu):   {acc_20:.1%} ± {std_20:.1%}")
    
    return ratio, acc_5, acc_10, acc_20
