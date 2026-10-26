#!/bin/bash

# 合并视频和音频的Shell脚本
# 用法: ./merge_video_audio.sh [目录路径]

# 设置目标目录（默认为当前目录）
target_dir="${1:-.}"

# 检查ffmpeg是否安装
if ! command -v ffmpeg &> /dev/null; then
    echo "错误: ffmpeg未安装，请先安装ffmpeg"
    echo "在基于Debian的系统上可尝试: sudo apt install ffmpeg"
    echo "在基于RHEL的系统上可尝试: sudo yum install ffmpeg"
    exit 1
fi

# 计数器
processed=0
skipped=0

echo "开始处理目录: $target_dir"
echo "----------------------------------------"

# 查找所有MP4文件并进行处理
find "$target_dir" -type f -iname "*.mp4" | while read -r video_file; do
    # 获取不带扩展名的文件名
    base_name="${video_file%.mp4}"
    base_name="${base_name%.MP4}"
    
    # 检查对应的M4A文件是否存在
    m4a_file="${base_name}.m4a"
    if [[ ! -f "$m4a_file" ]]; then
        m4a_file="${base_name}.M4A"
    fi
    
    if [[ -f "$m4a_file" ]]; then
        # 准备输出文件名（避免覆盖原始文件）
        output_file="${base_name}_merged.mp4"
        
        echo "处理中: $(basename "$video_file") + $(basename "$m4a_file")"
        echo "输出到: $(basename "$output_file")"
        
        # 执行合并操作
        ffmpeg -i "$video_file" -i "$m4a_file" -map 0:v -map 1:a -c copy -y "$output_file" &> /dev/null
        
        # 检查合并结果
        if [[ $? -eq 0 ]]; then
            echo "状态: 成功合并 ✓"
            ((processed++))
        else
            echo "状态: 合并失败 ❌"
        fi
        
        echo "----------------------------------------"
    else
        echo "跳过: $(basename "$video_file") - 未找到匹配的音频文件"
        echo "----------------------------------------"
        ((skipped++))
    fi
done

# 显示总结报告
echo "处理完成!"
echo "成功合并文件: $processed"
echo "跳过文件: $skipped"