from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
import arxiv
import os

class ArxivPipeline:

    def __init__(self):
        # 初始化客户端，并设置礼貌的抓取延迟和重试次数
        self.client = arxiv.Client(
            page_size = 100,
            #delay_seconds = 3,
            #num_retries = 5
        )
        self.preference = os.environ.get('CATEGORIES', 'cs.CV, cs.CL').split(',')
        self.preference = list(map(lambda x: x.strip(), self.preference))

    def process_item(self, item, spider):
        try:
            search = arxiv.Search(id_list=[item["id"]])
            result = next(self.client.results(search), None)
            
            if result:
                item["title"] = result.title
                item["authors"] = [author.name for author in result.authors]
                item["summary"] = result.summary
                # **新增**: 提取并保存arXiv官方的comment字段
                item["comment"] = result.comment
                item["cate"] = result.primary_category
                # 使用PDF链接作为URL，更直接
                item["url"] = result.pdf_url
                return item
            else:
                raise DropItem(f"Paper with ID {item['id']} not found on arXiv.")

        except Exception as e:
            spider.logger.error(f"Failed to process paper {item['id']}: {e}")
            raise DropItem(f"Failed to process paper {item['id']} due to an error.")