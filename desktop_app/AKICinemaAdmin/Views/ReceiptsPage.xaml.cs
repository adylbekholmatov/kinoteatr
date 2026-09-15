using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using AKICinemaAdmin.Models;

namespace AKICinemaAdmin.Views;

public partial class ReceiptsPage : Page
{
    public event Action? ReceiptsRefreshed;

    private List<PendingReceipt> _receipts = new();

    public ReceiptsPage()
    {
        InitializeComponent();
        Loaded += async (_, _) => await LoadAsync();
    }

    private async System.Threading.Tasks.Task LoadAsync()
    {
        _receipts = await App.Api.GetPendingReceiptsAsync();
        ReceiptsList.ItemsSource = null;
        ReceiptsList.ItemsSource = _receipts;

        bool empty = _receipts.Count == 0;
        EmptyState.Visibility  = empty ? Visibility.Visible : Visibility.Collapsed;
        TableScroll.Visibility = empty ? Visibility.Collapsed : Visibility.Visible;

        int pending   = _receipts.Count(r => !r.IsCancelledByClient);
        int cancelled = _receipts.Count - pending;

        CountLabel.Text = cancelled > 0
            ? $"{pending} ожидают · {cancelled} отменено"
            : $"{pending} ожидают";
    }

    private async void RefreshBtn_Click(object sender, RoutedEventArgs e)
    {
        await LoadAsync();
        ReceiptsRefreshed?.Invoke();
    }

    private void ViewReceipt_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string url && !string.IsNullOrEmpty(url))
        {
            try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); }
            catch { MessageBox.Show("Не удалось открыть чек.", "Ошибка"); }
        }
    }

    private async void Confirm_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button btn || btn.Tag is not int pk) return;

        btn.IsEnabled = false;
        var (success, error) = await App.Api.ConfirmBookingAsync(pk);
        btn.IsEnabled = true;

        if (success)
        {
            MessageBox.Show("Оплата подтверждена! Уведомление отправлено клиенту.", "Успех",
                            MessageBoxButton.OK, MessageBoxImage.Information);
            await LoadAsync();
            ReceiptsRefreshed?.Invoke();
        }
        else
        {
            MessageBox.Show($"Ошибка: {error}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async void Reject_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button btn || btn.Tag is not int pk) return;

        var note = ShowNoteDialog("Укажите причину отклонения (необязательно):");
        if (note == null) return;   // нажали «Отмена» — бронь не трогаем

        btn.IsEnabled = false;
        var (success, error) = await App.Api.RejectBookingAsync(pk, note);
        btn.IsEnabled = true;

        if (success)
        {
            MessageBox.Show("Бронирование отклонено. Клиент уведомлён.", "Готово",
                            MessageBoxButton.OK, MessageBoxImage.Information);
            await LoadAsync();
            ReceiptsRefreshed?.Invoke();
        }
        else
        {
            MessageBox.Show($"Ошибка: {error}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async void RequestTopup_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button btn || btn.Tag is not int pk) return;

        var note = ShowNoteDialog("Сколько не хватает? Текст увидит клиент:");
        if (note == null) return;

        btn.IsEnabled = false;
        var (success, error) = await App.Api.RequestTopupAsync(pk, note);
        btn.IsEnabled = true;

        if (success)
        {
            MessageBox.Show("Запрос доплаты отправлен. Клиент загрузит новый чек.",
                            "Готово", MessageBoxButton.OK, MessageBoxImage.Information);
            await LoadAsync();
            ReceiptsRefreshed?.Invoke();
        }
        else
        {
            MessageBox.Show($"Ошибка: {error}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async void Restore_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button btn || btn.Tag is not int pk) return;

        var result = MessageBox.Show(
            "Восстановить бронь? Клиент получит уведомление на сайте.",
            "Восстановить бронирование",
            MessageBoxButton.YesNo, MessageBoxImage.Question);

        if (result != MessageBoxResult.Yes) return;

        btn.IsEnabled = false;
        var (success, error) = await App.Api.RestoreBookingAsync(pk);
        btn.IsEnabled = true;

        if (success)
        {
            MessageBox.Show("Бронь восстановлена! Клиент получил уведомление.", "Готово",
                            MessageBoxButton.OK, MessageBoxImage.Information);
            await LoadAsync();
            ReceiptsRefreshed?.Invoke();
        }
        else
        {
            MessageBox.Show($"Ошибка: {error}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    /// <summary>Текст из диалога, либо null если нажали «Отмена».</summary>
    private static string? ShowNoteDialog(string prompt)
    {
        var dlg = new Window
        {
            Title = "Причина отклонения",
            Width = 420, Height = 180,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            ResizeMode = ResizeMode.NoResize,
            Background = new SolidColorBrush(Color.FromRgb(15, 15, 26)),
        };
        var panel = new StackPanel { Margin = new Thickness(16) };
        panel.Children.Add(new TextBlock
        {
            Text = prompt, Foreground = Brushes.White,
            FontSize = 13, Margin = new Thickness(0, 0, 0, 8)
        });
        var tb = new TextBox
        {
            Height = 36, FontSize = 13,
            Background = new SolidColorBrush(Color.FromRgb(30, 30, 50)),
            Foreground = Brushes.White,
            BorderBrush = new SolidColorBrush(Color.FromRgb(60, 60, 90)),
            Padding = new Thickness(8, 6, 8, 6)
        };
        panel.Children.Add(tb);
        var btnRow = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 10, 0, 0) };
        var ok  = new Button { Content = "OK",     Width = 70, Height = 30, Margin = new Thickness(0,0,6,0) };
        var cancel = new Button { Content = "Отмена", Width = 70, Height = 30 };
        string? result = null;
        ok.Click     += (_, _) => { result = tb.Text.Trim(); dlg.DialogResult = true; };
        cancel.Click += (_, _) => { dlg.DialogResult = false; };
        btnRow.Children.Add(ok);
        btnRow.Children.Add(cancel);
        panel.Children.Add(btnRow);
        dlg.Content = panel;
        dlg.ShowDialog();
        return result;
    }
}
