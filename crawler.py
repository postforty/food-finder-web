
import re
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

def get_element_text(driver, by, selector):
    try:
        return driver.find_element(by, selector).text
    except NoSuchElementException:
        return None

def get_element_attribute(driver, by, selector, attribute):
    try:
        return driver.find_element(by, selector).get_attribute(attribute)
    except NoSuchElementException:
        return None

def crawl_data(url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ko-KR")
    options.add_experimental_option('prefs', {'intl.accept_languages': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'})

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url)

        wait = WebDriverWait(driver, 20) # 대기 시간 증가
        wait.until(EC.presence_of_element_located((By.ID, "entryIframe")))

        driver.switch_to.frame("entryIframe")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".GHAhO")))
        except TimeoutException:
            pass 

        data = {}
        data['title'] = get_element_text(driver, By.CSS_SELECTOR, ".GHAhO")
        data['category'] = get_element_text(driver, By.CSS_SELECTOR, ".lnJFt")
        
        visitor_reviews_text = get_element_text(driver, By.CSS_SELECTOR, 'a[href*="review/visitor"]')
        if visitor_reviews_text:
            match = re.search(r'(\d+)', visitor_reviews_text.replace(',', ''))
            data['visitorReviews'] = int(match.group(0)) if match else None
        else:
            data['visitorReviews'] = None

        blog_reviews_text = get_element_text(driver, By.CSS_SELECTOR, 'a[href*="review/ugc"]')
        if blog_reviews_text:
            match = re.search(r'(\d+)', blog_reviews_text.replace(',', ''))
            data['blogReviews'] = int(match.group(0)) if match else None
        else:
            data['blogReviews'] = None

        data['description'] = get_element_text(driver, By.CSS_SELECTOR, ".XtBbS")
        data['address'] = get_element_text(driver, By.CSS_SELECTOR, ".LDgIH")
        
        hours_text = get_element_text(driver, By.CSS_SELECTOR, ".A_cdD")
        data['businessHours'] = hours_text.replace('\\n', ' ') if hours_text else None

        data['phone'] = get_element_text(driver, By.CSS_SELECTOR, ".xlx7Q")
        data['imageUrl'] = get_element_attribute(driver, By.CSS_SELECTOR, ".fNygA img", "src")
        data['url'] = url

        if not data['title']:
            return {"error": "필수 정보(title)를 찾지 못했습니다.", "url": url}

        return data

    except Exception as e:
        return {"error": str(e), "url": url}
    finally:
        driver.quit()

class CrawlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("네이버 지도 식당 정보 크롤러")
        self.root.geometry("800x600")
        self.json_file = "list.json"
        self.crawl_list = []

        main_pane = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_pane.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        left_pane = ttk.Frame(main_pane)
        main_pane.add(left_pane, weight=1)
        
        right_pane = ttk.Frame(main_pane)
        main_pane.add(right_pane, weight=1)
        
        existing_frame = ttk.LabelFrame(left_pane, text="기존 대상 목록")
        existing_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        
        self.existing_listbox = tk.Listbox(existing_frame)
        self.existing_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ex_scrollbar = ttk.Scrollbar(existing_frame, orient=tk.VERTICAL, command=self.existing_listbox.yview)
        ex_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.existing_listbox.config(yscrollcommand=ex_scrollbar.set)
        
        self.delete_existing_button = ttk.Button(left_pane, text="선택한 기존 항목 삭제", command=self.delete_existing_item)
        self.delete_existing_button.pack(fill=tk.X, pady=5)

        self.recrawl_button = ttk.Button(left_pane, text="기존 항목 다시 크롤링", command=self.start_recrawl)
        self.recrawl_button.pack(fill=tk.X, pady=(0, 10))

        new_frame = ttk.LabelFrame(left_pane, text="신규 대상 목록")
        new_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        
        self.new_listbox = tk.Listbox(new_frame)
        self.new_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        new_scrollbar = ttk.Scrollbar(new_frame, orient=tk.VERTICAL, command=self.new_listbox.yview)
        new_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.new_listbox.config(yscrollcommand=new_scrollbar.set)

        self.delete_new_button = ttk.Button(left_pane, text="선택한 신규 항목 삭제", command=self.delete_new_item)
        self.delete_new_button.pack(fill=tk.X, pady=5)

        # 신규 URL 추가 인풋창을 신규 대상 목록 창 아래에 배치
        add_frame = ttk.Frame(left_pane)
        add_frame.pack(fill=tk.X, pady=(10, 0))
        self.url_entry = ttk.Entry(add_frame)
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        self.add_button = ttk.Button(add_frame, text="신규 URL 추가", command=self.add_url)
        self.add_button.pack(side=tk.LEFT)

        # 신규 목록 전체 크롤링 버튼을 신규 URL 추가 인풋창 아래로 위치
        self.crawl_button = ttk.Button(left_pane, text="신규 목록 전체 크롤링", command=self.start_crawling_new)
        self.crawl_button.pack(fill=tk.X, pady=10)
        
        # --- 우측 패널 (컨트롤) ---
        # 결과
        result_frame = ttk.LabelFrame(right_pane, text="결과 보고서")
        result_frame.pack(fill=tk.BOTH, expand=True)
                # width를 10~20 정도로 작게 설정합니다.
        # pack(expand=True, fill=tk.BOTH)가 설정되어 있으므로,
        # 실제 화면에서는 남는 공간을 모두 채우며 늘어납니다.
        self.result_text = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, width=35)
        self.result_text.pack(expand=True, fill=tk.BOTH)

        self.result_queue = queue.Queue()
        self.load_list()

    def get_item_display_text(self, item):
        title, url = item.get("title"), item.get("url")
        return f"{title} - {url}" if title and title != url else url

    def load_list(self):
        self.existing_listbox.delete(0, tk.END)
        self.new_listbox.delete(0, tk.END)
        if os.path.exists(self.json_file):
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.crawl_list = json.load(f)
            for item in self.crawl_list:
                display_text = self.get_item_display_text(item)
                if item.get("title"):
                    self.existing_listbox.insert(tk.END, display_text)
                else:
                    self.new_listbox.insert(tk.END, display_text)
    
    def save_list(self):
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.crawl_list, f, ensure_ascii=False, indent=2)

    def add_url(self):
        url = self.url_entry.get().strip()
        if not url: return
        if any(item.get("url") == url for item in self.crawl_list):
            messagebox.showwarning("중복 오류", "이미 목록에 있는 URL입니다.")
            return
        new_item = {"url": url}
        self.crawl_list.append(new_item)
        # self.save_list() # 신규 URL 추가 시 list.json에 즉시 저장하지 않음
        self.new_listbox.insert(tk.END, self.get_item_display_text(new_item))
        self.url_entry.delete(0, tk.END)

    def find_item_index_in_master_list(self, display_text):
        for i, item in enumerate(self.crawl_list):
            if self.get_item_display_text(item) == display_text:
                return i
        return -1

    def delete_existing_item(self):
        indices = self.existing_listbox.curselection()
        if not indices: return
        selected_text = self.existing_listbox.get(indices[0])
        master_index = self.find_item_index_in_master_list(selected_text)
        if master_index != -1:
            del self.crawl_list[master_index]
            self.save_list()
            self.load_list()

    def delete_new_item(self):
        indices = self.new_listbox.curselection()
        if not indices: return
        selected_text = self.new_listbox.get(indices[0])
        master_index = self.find_item_index_in_master_list(selected_text)
        if master_index != -1:
            del self.crawl_list[master_index]
            self.save_list()
            self.load_list()

    def start_crawling_new(self):
        items_to_crawl = [item for item in self.crawl_list if not item.get('title')]
        if not items_to_crawl: return
        self.run_crawl_task("신규 항목 크롤링", items_to_crawl)

    def start_recrawl(self):
        items_to_crawl = [item for item in self.crawl_list if item.get('title')]
        if not items_to_crawl: return
        
        # In recrawl, we rebuild the crawled list
        newly_crawled_data = []
        uncrawled_items = [item for item in self.crawl_list if not item.get('title')]
        
        self.run_crawl_task("기존 항목 다시 크롤링", items_to_crawl, newly_crawled_data, uncrawled_items)

    def run_crawl_task(self, task_name, items_to_crawl, *args):
        self.toggle_controls(tk.DISABLED)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"--- {task_name} 시작 ({len(items_to_crawl)}개) ---\n\n")
        
        self.success_count = 0
        self.fail_count = 0
        
        thread_args = (items_to_crawl, *args)
        threading.Thread(target=self.run_crawl_thread, args=thread_args, daemon=True).start()
        self.root.after(100, self.check_crawl_queue)

    def run_crawl_thread(self, items_to_crawl, newly_crawled_data=None, uncrawled_items=None):
        for item_data in items_to_crawl:
            result = crawl_data(item_data['url'])
            
            # Pass metadata to the queue
            queue_item = {"result": result}
            if newly_crawled_data is not None:
                queue_item["context"] = "recrawl"
                queue_item["newly_crawled_data"] = newly_crawled_data
                queue_item["uncrawled_items"] = uncrawled_items
            else:
                queue_item["context"] = "new_crawl"
            
            self.result_queue.put(queue_item)
        self.result_queue.put({"status": "finished"})

    def check_crawl_queue(self):
        try:
            queue_item = self.result_queue.get_nowait()
            if queue_item.get("status") == "finished":
                self.result_text.insert(tk.END, f"\n--- 작업 완료: 총 {self.success_count + self.fail_count}개 중 {self.success_count}개 성공, {self.fail_count}개 실패 ---\n")
                self.toggle_controls(tk.NORMAL)
                self.load_list()
                return

            result = queue_item["result"]
            context = queue_item["context"]
            url = result.get('url', 'N/A')
            
            if "error" in result:
                self.fail_count += 1
                self.result_text.insert(tk.END, f"[실패] {url}\n  └ 사유: {result['error']}\n\n")
            else:
                self.success_count += 1
                title = result.get('title', 'N/A')
                self.result_text.insert(tk.END, f"[성공] {title} ({url})\n\n")
                
                if context == "recrawl":
                    queue_item["newly_crawled_data"].append(result)
                    self.crawl_list = queue_item["newly_crawled_data"] + queue_item["uncrawled_items"]
                else: # new_crawl
                    for i, item in enumerate(self.crawl_list):
                        if item.get('url') == url:
                            self.crawl_list[i].update(result)
                            break
                self.save_list()

            self.root.after(100, self.check_crawl_queue)
        except queue.Empty:
            self.root.after(100, self.check_crawl_queue)

    def toggle_controls(self, state):
        for widget in [self.crawl_button, self.add_button, self.delete_existing_button, self.delete_new_button, self.recrawl_button, self.url_entry, self.existing_listbox, self.new_listbox]:
            widget.config(state=state)

if __name__ == "__main__":
    root = tk.Tk()
    app = CrawlApp(root)
    root.mainloop()
