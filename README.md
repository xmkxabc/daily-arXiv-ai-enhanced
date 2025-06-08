# AI增强的arXiv每日速报 (AI-Enhanced Daily arXiv)

一个每日自动更新的、由AI分析和翻译的计算机科学领域论文速报。

This tool will daily crawl https://arxiv.org and use LLMs to summarize them.

## How to use
This repo will daily crawl arXiv papers about **cs.CV, cs.GR and cs.CL**, and use **DeepSeek** to summarize the papers in **Chinese**.
If you wish to crawl other arXiv categories, use other LLMs or other languages, please follow the bellow instructions.
Otherwise, you can directly use this repo. Please star it if you like :)

**Instructions:**
1. Fork this repo to your own account
2. Go to: your-own-repo -> Settings -> Secrets and variables -> Actions
3. Go to Secrets. Secrets are encrypted and are used for sensitive data
4. Create two repository secrets named `OPENAI_API_KEY` and `OPENAI_BASE_URL`, and input corresponding values.
5. Go to Variables. Variables are shown as plain text and are used for non-sensitive data
6. Create the following repository variables:
   1. `CATEGORIES`: separate the categories with ",", such as "cs.CL, cs.CV"
   2. `LANGUAGE`: such as "Chinese" or "English"
   3. `MODEL_NAME`: such as "deepseek-chat"
   4. `EMAIL`: your email for push to github
   5. `NAME`: your name for push to github
7. Go to your-own-repo -> Actions -> arXiv-daily-ai-enhanced
8. You can manually click **Run workflow** to test if it works well (it may takes about one hour). 
By default, this action will automatically run every day
You can modify it in `.github/workflows/run.yml`
9. If you wish to modify the content in `README.md`, do not directly edit README.md. You should edit `template.md`.

---

## **最新速报：2025-06-08**

**今日领域分布:** 

> [**阅读 2025-06-08 的完整报告...**](./data/2025-06-08.md)

---

### **本周回顾 (Past 7 Days)**

- [2025-06-07](./data/2025-06-07.md)
- [2025-06-06](./data/2025-06-06.md)
- [2025-06-05](./data/2025-06-05.md)
- [2025-06-04](./data/2025-06-04.md)
- [2025-06-03](./data/2025-06-03.md)
- [2025-06-02](./data/2025-06-02.md)


---

### 近期日历 (Recent Calendar)

#### June 2025

| 一 (Mon) | 二 (Tue) | 三 (Wed) | 四 (Thu) | 五 (Fri) | 六 (Sat) | 日 (Sun) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
|   |   |   |   |   |   | [1](./data/2025-06-01.md) |
| [2](./data/2025-06-02.md) | [3](./data/2025-06-03.md) | [4](./data/2025-06-04.md) | [5](./data/2025-06-05.md) | [6](./data/2025-06-06.md) | [7](./data/2025-06-07.md) | [8](./data/2025-06-08.md) |
| 9 | 10 | 11 | 12 | 13 | 14 | 15 |
| 16 | 17 | 18 | 19 | 20 | 21 | 22 |
| 23 | 24 | 25 | 26 | 27 | 28 | 29 |
| 30 |   |   |   |   |   |   |


#### May 2025

| 一 (Mon) | 二 (Tue) | 三 (Wed) | 四 (Thu) | 五 (Fri) | 六 (Sat) | 日 (Sun) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
|   |   |   | [1](./data/2025-05-01.md) | [2](./data/2025-05-02.md) | [3](./data/2025-05-03.md) | [4](./data/2025-05-04.md) |
| [5](./data/2025-05-05.md) | [6](./data/2025-05-06.md) | [7](./data/2025-05-07.md) | [8](./data/2025-05-08.md) | [9](./data/2025-05-09.md) | [10](./data/2025-05-10.md) | [11](./data/2025-05-11.md) |
| [12](./data/2025-05-12.md) | [13](./data/2025-05-13.md) | [14](./data/2025-05-14.md) | [15](./data/2025-05-15.md) | [16](./data/2025-05-16.md) | [17](./data/2025-05-17.md) | [18](./data/2025-05-18.md) |
| [19](./data/2025-05-19.md) | [20](./data/2025-05-20.md) | [21](./data/2025-05-21.md) | [22](./data/2025-05-22.md) | [23](./data/2025-05-23.md) | [24](./data/2025-05-24.md) | [25](./data/2025-05-25.md) |
| [26](./data/2025-05-26.md) | [27](./data/2025-05-27.md) | [28](./data/2025-05-28.md) | [29](./data/2025-05-29.md) | [30](./data/2025-05-30.md) | [31](./data/2025-05-31.md) |   |


---

### **历史存档 (Full Archive)**

<details>
<summary><strong>2025</strong></summary>

<details>
<summary>April</summary>

- [2025-04-30](./data/2025-04-30.md)
- [2025-04-29](./data/2025-04-29.md)
- [2025-04-28](./data/2025-04-28.md)
- [2025-04-27](./data/2025-04-27.md)
- [2025-04-26](./data/2025-04-26.md)
- [2025-04-25](./data/2025-04-25.md)
- [2025-04-24](./data/2025-04-24.md)
- [2025-04-23](./data/2025-04-23.md)
- [2025-04-22](./data/2025-04-22.md)
- [2025-04-21](./data/2025-04-21.md)
- [2025-04-20](./data/2025-04-20.md)
- [2025-04-19](./data/2025-04-19.md)
- [2025-04-18](./data/2025-04-18.md)
- [2025-04-17](./data/2025-04-17.md)
- [2025-04-16](./data/2025-04-16.md)
- [2025-04-15](./data/2025-04-15.md)
- [2025-04-14](./data/2025-04-14.md)
- [2025-04-13](./data/2025-04-13.md)
- [2025-04-12](./data/2025-04-12.md)
- [2025-04-11](./data/2025-04-11.md)
- [2025-04-10](./data/2025-04-10.md)
- [2025-04-09](./data/2025-04-09.md)
- [2025-04-08](./data/2025-04-08.md)
- [2025-04-07](./data/2025-04-07.md)
- [2025-04-06](./data/2025-04-06.md)
- [2025-04-05](./data/2025-04-05.md)
- [2025-04-04](./data/2025-04-04.md)
- [2025-04-03](./data/2025-04-03.md)
- [2025-04-02](./data/2025-04-02.md)
- [2025-04-01](./data/2025-04-01.md)

</details>
<details>
<summary>March</summary>

- [2025-03-31](./data/2025-03-31.md)
- [2025-03-30](./data/2025-03-30.md)
- [2025-03-29](./data/2025-03-29.md)
- [2025-03-28](./data/2025-03-28.md)
- [2025-03-27](./data/2025-03-27.md)
- [2025-03-26](./data/2025-03-26.md)
- [2025-03-25](./data/2025-03-25.md)
- [2025-03-24](./data/2025-03-24.md)
- [2025-03-23](./data/2025-03-23.md)
- [2025-03-22](./data/2025-03-22.md)
- [2025-03-21](./data/2025-03-21.md)
- [2025-03-20](./data/2025-03-20.md)
- [2025-03-19](./data/2025-03-19.md)
- [2025-03-18](./data/2025-03-18.md)

</details>

</details>


---
*This page is automatically updated by a GitHub Action.*