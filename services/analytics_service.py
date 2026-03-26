"""
Analytics Service
==================
جلب engagement metrics من كل منصة تلقائياً.

المنصات المدعومة:
  Facebook  : Graph API — likes, comments, shares, reach, impressions
  Instagram : Graph API — likes, comments, reach, impressions, saved
  Threads   : Threads API — likes, replies, reposts, views
  LinkedIn  : UGC Posts API — likes, comments, shares, impressions
  Twitter/X : Tweepy v2 — likes, retweets, replies, impressions
"""

import logging
import requests

logger = logging.getLogger(__name__)

GRAPH_VER = "v20.0"


# ── Facebook ──────────────────────────────────────────────────────────────────

def fetch_facebook_metrics(post_id: str, access_token: str) -> dict:
    """
    Fetch engagement metrics for a Facebook post.
    post_id: the id returned when posting (page_post_id format: pageId_postId)
    """
    try:
        fields = "likes.summary(true),comments.summary(true),shares,impressions"
        r = requests.get(
            f"https://graph.facebook.com/{GRAPH_VER}/{post_id}",
            params={"fields": fields, "access_token": access_token},
            timeout=15,
        )
        if not r.ok:
            return {}
        d = r.json()
        return {
            "likes":       d.get("likes", {}).get("summary", {}).get("total_count", 0),
            "comments":    d.get("comments", {}).get("summary", {}).get("total_count", 0),
            "shares":      d.get("shares", {}).get("count", 0),
            "impressions": d.get("impressions", 0),
        }
    except Exception as e:
        logger.warning(f"Facebook metrics fetch failed for {post_id}: {e}")
        return {}


# ── Instagram ─────────────────────────────────────────────────────────────────

def fetch_instagram_metrics(post_id: str, access_token: str) -> dict:
    """Fetch engagement metrics for an Instagram media post."""
    try:
        fields = "like_count,comments_count,reach,impressions,saved"
        r = requests.get(
            f"https://graph.facebook.com/{GRAPH_VER}/{post_id}",
            params={"fields": fields, "access_token": access_token},
            timeout=15,
        )
        if not r.ok:
            return {}
        d = r.json()
        return {
            "likes":       d.get("like_count", 0),
            "comments":    d.get("comments_count", 0),
            "impressions": d.get("impressions", 0),
            "reach":       d.get("reach", 0),
            "saved":       d.get("saved", 0),
        }
    except Exception as e:
        logger.warning(f"Instagram metrics fetch failed for {post_id}: {e}")
        return {}


# ── Threads ───────────────────────────────────────────────────────────────────

def fetch_threads_metrics(post_id: str, access_token: str) -> dict:
    """Fetch engagement metrics for a Threads post."""
    try:
        fields = "likes,replies,reposts,views"
        r = requests.get(
            f"https://graph.threads.net/v1.0/{post_id}/insights",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"metric": "likes,replies,reposts,views"},
            timeout=15,
        )
        if not r.ok:
            return {}
        data = r.json().get("data", [])
        result = {}
        for item in data:
            name  = item.get("name", "")
            value = item.get("values", [{}])[0].get("value", 0) if item.get("values") else item.get("total_value", {}).get("value", 0)
            result[name] = value
        return {
            "likes":    result.get("likes", 0),
            "comments": result.get("replies", 0),
            "shares":   result.get("reposts", 0),
            "impressions": result.get("views", 0),
        }
    except Exception as e:
        logger.warning(f"Threads metrics fetch failed for {post_id}: {e}")
        return {}


# ── LinkedIn ──────────────────────────────────────────────────────────────────

def fetch_linkedin_metrics(post_id: str, access_token: str) -> dict:
    """Fetch engagement metrics for a LinkedIn UGC post."""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        # Social actions (likes, comments, shares)
        encoded_id = requests.utils.quote(post_id, safe='')
        r = requests.get(
            f"https://api.linkedin.com/v2/socialActions/{encoded_id}",
            headers=headers,
            timeout=15,
        )
        result = {}
        if r.ok:
            d = r.json()
            result["likes"]    = d.get("likesSummary", {}).get("totalLikes", 0)
            result["comments"] = d.get("commentsSummary", {}).get("totalFirstLevelComments", 0)
            result["shares"]   = d.get("sharesSummary", {}).get("totalShares", 0)

        # Impressions via analytics
        r2 = requests.get(
            "https://api.linkedin.com/v2/organizationalEntityShareStatistics",
            headers=headers,
            params={"q": "organizationalEntity", "shares[0]": post_id},
            timeout=15,
        )
        if r2.ok:
            elements = r2.json().get("elements", [])
            if elements:
                stats = elements[0].get("totalShareStatistics", {})
                result["impressions"] = stats.get("impressionCount", 0)
                result["clicks"]      = stats.get("clickCount", 0)

        return result
    except Exception as e:
        logger.warning(f"LinkedIn metrics fetch failed for {post_id}: {e}")
        return {}


# ── Twitter / X ───────────────────────────────────────────────────────────────

def fetch_twitter_metrics(tweet_id: str, api_key: str, api_secret: str,
                           access_token: str, access_token_secret: str) -> dict:
    """Fetch engagement metrics for a tweet."""
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=api_key, consumer_secret=api_secret,
            access_token=access_token, access_token_secret=access_token_secret,
        )
        tweet = client.get_tweet(
            tweet_id,
            tweet_fields=["public_metrics", "non_public_metrics", "organic_metrics"],
        )
        if not tweet.data:
            return {}
        pm = tweet.data.public_metrics or {}
        return {
            "likes":       pm.get("like_count", 0),
            "comments":    pm.get("reply_count", 0),
            "shares":      pm.get("retweet_count", 0),
            "impressions": pm.get("impression_count", 0),
            "quotes":      pm.get("quote_count", 0),
        }
    except Exception as e:
        logger.warning(f"Twitter metrics fetch failed for {tweet_id}: {e}")
        return {}


# ── Unified fetcher ───────────────────────────────────────────────────────────

def fetch_post_metrics(post) -> dict:
    """
    Fetch metrics for all platforms a post was published to.
    Returns merged dict with totals.
    """
    from database.models import Config

    cfg = {
        "fb_access_token":             Config.get("fb_access_token", ""),
        "ig_access_token":             Config.get("ig_access_token", ""),
        "threads_access_token":        Config.get("threads_access_token", ""),
        "li_access_token":             Config.get("li_access_token", ""),
        "twitter_api_key":             Config.get("twitter_api_key", ""),
        "twitter_api_secret":          Config.get("twitter_api_secret", ""),
        "twitter_access_token":        Config.get("twitter_access_token", ""),
        "twitter_access_token_secret": Config.get("twitter_access_token_secret", ""),
    }

    all_metrics = {}

    if post.fb_post_id and cfg["fb_access_token"]:
        m = fetch_facebook_metrics(post.fb_post_id, cfg["fb_access_token"])
        if m:
            all_metrics["facebook"] = m

    if post.ig_post_id and cfg["ig_access_token"]:
        m = fetch_instagram_metrics(post.ig_post_id, cfg["ig_access_token"])
        if m:
            all_metrics["instagram"] = m

    if post.threads_post_id and cfg["threads_access_token"]:
        m = fetch_threads_metrics(post.threads_post_id, cfg["threads_access_token"])
        if m:
            all_metrics["threads"] = m

    if post.linkedin_post_id and cfg["li_access_token"]:
        m = fetch_linkedin_metrics(post.linkedin_post_id, cfg["li_access_token"])
        if m:
            all_metrics["linkedin"] = m

    if (post.x_post_id and cfg["twitter_api_key"] and
            cfg["twitter_api_secret"] and cfg["twitter_access_token"]):
        m = fetch_twitter_metrics(
            post.x_post_id,
            cfg["twitter_api_key"], cfg["twitter_api_secret"],
            cfg["twitter_access_token"], cfg["twitter_access_token_secret"],
        )
        if m:
            all_metrics["twitter"] = m

    # Aggregate totals
    totals = {"likes": 0, "comments": 0, "shares": 0, "impressions": 0}
    for platform_metrics in all_metrics.values():
        for key in totals:
            totals[key] += platform_metrics.get(key, 0)

    # Engagement score = weighted sum
    score = (
        totals["likes"]    * 1 +
        totals["comments"] * 3 +
        totals["shares"]   * 5 +
        int(totals["impressions"] * 0.01)
    )

    return {
        "platforms": all_metrics,
        "totals":    totals,
        "score":     score,
    }


def update_post_metrics(post_id: int, app=None) -> dict:
    """
    Fetch and save metrics for a single post.
    Can be called from scheduler or manually.
    """
    ctx = app.app_context() if app else None
    if ctx:
        ctx.push()

    try:
        from database.models import db, Post
        post = Post.query.get(post_id)
        if not post or post.status != "POSTED":
            return {}

        metrics = fetch_post_metrics(post)
        if not metrics.get("totals"):
            return metrics

        t = metrics["totals"]
        post.likes       = t.get("likes", post.likes or 0)
        post.comments    = t.get("comments", post.comments or 0)
        post.shares      = t.get("shares", post.shares or 0)
        post.impressions = t.get("impressions", post.impressions or 0)
        post.engagement_score = metrics.get("score", post.engagement_score or 0)
        db.session.commit()

        logger.info(f"Updated metrics for post #{post_id}: score={post.engagement_score}")
        return metrics

    except Exception as e:
        logger.warning(f"update_post_metrics failed for #{post_id}: {e}")
        return {}
    finally:
        if ctx:
            ctx.pop()


def bulk_update_metrics(app=None, limit: int = 20):
    """
    Update metrics for the most recent POSTED posts.
    Called from APScheduler every few hours.
    """
    ctx = app.app_context() if app else None
    if ctx:
        ctx.push()

    try:
        from database.models import Post
        posts = (Post.query
                 .filter_by(status="POSTED")
                 .order_by(Post.posted_at.desc())
                 .limit(limit)
                 .all())

        updated = 0
        for post in posts:
            try:
                result = update_post_metrics(post.id)
                if result.get("score", 0) > 0:
                    updated += 1
            except Exception:
                pass

        logger.info(f"Bulk metrics update: {updated}/{len(posts)} posts updated")
        return updated

    except Exception as e:
        logger.warning(f"bulk_update_metrics failed: {e}")
        return 0
    finally:
        if ctx:
            ctx.pop()
