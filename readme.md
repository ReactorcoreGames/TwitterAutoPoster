# 🐦 Automated Twitter Poster 🤖

> Post to Twitter/X automatically on a schedule! Set it and forget it! 

## ✨ What is this?

This is a simple tool that automatically posts content to your Twitter/X account on a schedule. Just fill in a spreadsheet with your posts, set it up once, and it will handle the rest!

- 🕒 Posts automatically every 12 hours
- 📝 Cycles through your list of prepared posts
- 🔄 Works completely on its own after setup
- 🔗 Automatically creates Twitter cards for your links
- 🖼️ Includes images from your links when available
- 📱 No need to open Twitter or remember to post

## 🚀 Quick Setup Guide

### Step 1: Copy this repository 📋

1. Click the **Fork** button at the top right of this page
2. Name your new repository whatever you want (like "my-twitter-poster")
3. Click **Create fork**

Congrats! Now you have your own copy of this tool! 🎉

### Step 2: Prepare your posts 📝

1. In your new repository, find the `posts.csv` file and click on it
2. Click the **pencil icon** (Edit this file)
3. Add your posts in the format: 
   ```
   title,url,hashtags
   Check out my cool project!,https://example.com,#cool #project #awesome
   ```
4. Each row will become one tweet
5. Click **Commit changes** when done

### Step 3: Get your Twitter API Credentials 🔑

**Important:** You need Twitter API access (which requires approval) to use this tool.

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Apply for a developer account (if you don't have one)
3. Create a new App in your developer dashboard
4. Go to your App's "Keys and tokens" section
5. Generate and copy these **4 credentials**:
   - **API Key** (Consumer Key)
   - **API Key Secret** (Consumer Secret)
   - **Access Token** 
   - **Access Token Secret**
6. Copy all credentials immediately (you won't see the secrets again!)

**Note:** Twitter's API access requires approval and may take some time. Make sure you have a legitimate use case when applying.

### Step 4: Add your Twitter API credentials to GitHub 🔒

1. In your GitHub repository, click on **Settings**
2. In the left sidebar, click on **Secrets and variables** → **Actions**
3. Click **New repository secret** and create these **4 secrets**:
   - `TWITTER_API_KEY` - paste your API Key
   - `TWITTER_API_SECRET` - paste your API Key Secret
   - `TWITTER_ACCESS_TOKEN` - paste your Access Token
   - `TWITTER_ACCESS_TOKEN_SECRET` - paste your Access Token Secret

### Step 5: Create initial state file 📄

1. In your repository, click **Add file** → **Create new file**
2. Name it `state.json`
3. Add this content:
   ```json
   {
     "last_row_index": -1,
     "last_post_time": null
   }
   ```
4. Click **Commit changes**

### Step 6: Start the poster! 🎬

1. Click on the **Actions** tab in your repository
2. Click on **Twitter Poster** in the left sidebar
3. Click the **Run workflow** button
4. Click the green **Run workflow** button in the popup

Woohoo! 🎉 Your first tweet will be sent immediately, and then it will continue posting every 12 hours!

## 📊 How to check if it's working

1. Go to the **Actions** tab in your repository
2. Look for green checkmarks ✅ next to "Twitter Poster" runs
3. Click on any run to see the details
4. Check your Twitter profile to see your tweets!

## 🛠️ Customizing your posting schedule

Want to post more or less frequently? You can change the schedule by editing the `.github/workflows/poster.yml` file:

1. Click on the file and then the edit (pencil) icon
2. Find the line that says `cron: '0 */12 * * *'`
3. Change it to:
   - Every 6 hours: `0 */6 * * *`
   - Once a day: `0 12 * * *` (posts at 12:00 UTC)
   - Twice a day on weekdays only: `0 9,17 * * 1-5`

## ⚠️ Important Notes

- **Twitter API Limits**: Twitter has strict rate limits. Don't post too frequently or your API access might be suspended.
- **Content Guidelines**: Make sure your posts comply with Twitter's terms of service.
- **Character Limit**: Tweets are limited to 280 characters. The script will automatically trim hashtags if needed.
- **API Costs**: Twitter's API may have usage costs depending on your plan.

## 🤔 Troubleshooting

**Tweets not showing up?**
- Check the Actions tab for any red ❌ errors
- Verify your Twitter Bearer Token is correct and has necessary permissions
- Make sure your posts.csv file has the correct format
- Check that your Twitter developer account is in good standing

**Getting API errors?**
- Ensure your Twitter app has the correct permissions (Read and Write)
- Check if you've hit any rate limits
- Verify all 4 Twitter API credentials are correct and haven't expired
- Make sure your Access Token has write permissions

**Need to pause posting?**
- Go to Settings → Actions → General
- Scroll down and select "Disable Actions"

## 🌟 Tips and Tricks

- 💡 Keep URLs short to leave more room for your message
- 💡 Use hashtags strategically to reach more people
- 💡 Mix up your content to keep followers engaged
- 💡 You can manually trigger posts anytime from the Actions tab
- 💡 Twitter automatically creates link previews, so you don't need to describe the link

## 🔐 Security Best Practices

- Never share your Bearer Token publicly
- Use GitHub Secrets to store sensitive information
- Regularly review your Twitter app's permissions
- Monitor your API usage to avoid unexpected charges

## 📞 Need help?

Open an issue in this repository if you get stuck, and someone might be able to help you out!

---

Happy tweeting! 🐦✨

## 🔄 Differences from Bluesky Poster

If you're coming from the Bluesky version:
- Uses Twitter's Bearer Token instead of handle/password authentication
- Different character limit (280 vs 300)
- Different image upload process
- Automatic Twitter card generation for links
- Requires Twitter Developer Account approval