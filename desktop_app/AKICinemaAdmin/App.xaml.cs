using System.Windows;
using AKICinemaAdmin.Services;

namespace AKICinemaAdmin;

public partial class App : Application
{
    public static ApiService Api { get; } = new ApiService();
}
